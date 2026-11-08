import re, json, sys, threading, http.server, functools
from playwright.sync_api import sync_playwright
ROOT='/home/claude/nabucha-site'
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8080),functools.partial(http.server.SimpleHTTPRequestHandler,directory=ROOT))
threading.Thread(target=srv.serve_forever,daemon=True).start()
RESP={"texto":"Orçamento para a Dona Marta, no bairro Centro. Quarto da menina 3 e meio por 4...","dados":{"cliente_nome":"Dona Marta","cliente_local":"Centro","modo":"","dias":4,"ajudantes":1,"comodos":[{"nome":"quarto da menina","largura":3.5,"comprimento":4,"pe_direito":2.6,"area_paredes":None,"area_teto":None,"pintar_teto":True,"portas":None,"janelas":None},{"nome":"Sala","largura":5,"comprimento":6,"pe_direito":None,"area_paredes":None,"area_teto":None,"pintar_teto":False,"portas":None,"janelas":None},{"nome":"cozinha","largura":None,"comprimento":None,"pe_direito":None,"area_paredes":None,"area_teto":None,"pintar_teto":None,"portas":None,"janelas":None}],"situacoes":["cor","repintura"],"reparos":["mofo","furos"],"acabamento":"acet","massa_corrida":False,"textura":True,"prazo":"","obs":""}}
modo={'v':'ok'}
erros=[];falhas=[]
def ok(c,m):
    print(('OK   ' if c else 'FALHA ')+m)
    if not c: falhas.append(m)
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream','--autoplay-policy=no-user-gesture-required'])
    ctx=b.new_context(viewport={'width':390,'height':844},permissions=['microphone'])
    pg=ctx.new_page()
    pg.on('pageerror',lambda e:erros.append(str(e)))
    def rota(route):
        if modo['v']=='ok': route.fulfill(status=200,content_type='application/json',body=json.dumps(RESP))
        else: route.fulfill(status=502,content_type='application/json',body=json.dumps({"erro":"Não consegui ouvir o áudio agora"}))
    pg.route(re.compile(r'workers\.dev'),rota)
    pg.route('**/fonts.googleapis.com/**',lambda r:r.abort()); pg.route('**/fonts.gstatic.com/**',lambda r:r.abort())
    pg.goto('http://localhost:8080/orcamento/'); pg.evaluate('localStorage.clear()'); pg.reload()
    est=lambda: pg.get_attribute('#voz','data-estado')
    vis=lambda sel: pg.is_visible(sel)
    ok(vis('#entrada') and not vis('#voz') and not vis('#c-nome') and not vis('#rooms-card') and not vis('#next'),'começo: só a escolha falar / na mão')
    pg.click('[data-entrada="mao"] >> nth=0'); pg.wait_for_timeout(300)
    ok(not vis('#entrada') and not vis('#voz') and vis('#c-nome') and vis('#rooms-card') and vis('#next'),'na mão: todos os campos, sem áudio')
    pg.evaluate('localStorage.clear()'); pg.reload()
    antes=pg.locator('.room').count(); nome0=pg.input_value('#c-nome')
    # falar: já começa a gravar
    pg.click('#entrada [data-entrada="voz"]'); pg.wait_for_timeout(1500)
    ok(est()=='gravando' and vis('#voz-enviar') and not vis('#c-nome') and not vis('#voz-mao'),'Falar o serviço já grava, sem campos misturados')
    pg.click('#voz-cancelar'); pg.wait_for_timeout(800); ok(est()=='pronto' and pg.locator('.room').count()==antes,'Cancelar não envia nada')
    # áudio curto
    pg.click('#voz-gravar'); pg.wait_for_timeout(500); pg.click('#voz-enviar'); pg.wait_for_function("document.querySelector('#voz').dataset.estado!=='enviando'&&document.querySelector('#voz').dataset.estado!=='gravando'",timeout=15000)
    ok(est()=='erro' and 'curto' in pg.inner_text('#voz-erro-txt'),'áudio curto avisa')
    # fluxo completo
    pg.click('#voz-gravar'); pg.wait_for_timeout(3500); pg.click('#voz-enviar')
    pg.wait_for_function("document.querySelector('#voz').dataset.estado==='feito'",timeout=20000)
    txt=pg.inner_text('#voz-res'); print('   ->',txt.replace('\n',' | '))
    ok(pg.locator('.room, .room-mini').count()==3,'exemplo sai e entram os 3 cômodos do áudio')
    ok(pg.locator('.room-mini').count()==2 and pg.locator('.room').count()==1,'cômodos certos ficam em resumo; só o que falta fica aberto')
    ok(vis('#c-nome') and vis('#rooms-card') and vis('#dias-card') and not vis('#jeito'),'depois do áudio: só cliente, dias e cômodos (jeito não foi falado)')
    ok('Parede e serviço' in txt and 'mudar de cor' in txt,'resumo da parede no cartão')
    ok(vis('#voz-todos') and vis('#next'),'link Ver todos os campos e Avançar aparecem')
    ok(pg.input_value('#c-nome')=='Dona Marta','nome do cliente preenchido')
    ok(pg.locator('.room.falta').count()==1,'cozinha sem medida marcada em vermelho')
    ok('medidas de Cozinha' in txt,'Falta: medidas de Cozinha')
    st=pg.evaluate("JSON.parse(localStorage.getItem('nabucha-proto-v5')).O")
    ok(st['situs']==['cor'],'mudar de cor sem repintura')
    ok(st['rep'].get('mofo') and st['rep'].get('furos'),'mofo e furos marcados')
    ok(st['acab']=='acet' and st['diasM']=='4' and st['ajud']==1,'acetinado, 4 dias, 1 ajudante')
    ok(st['sv']['textura']['on'] and st['sv']['pint']['dem']==3,'textura ligada, pintura 3 demãos')
    r0=[r for r in st['rooms'] if r['nome']=='Quarto da menina']
    ok(r0 and r0[0]['l']=='3,5' and r0[0]['h']=='2,6','quarto 3,5 x 4, pé-direito 2,6')
    # digitar medida tira o vermelho
    cz=pg.locator('.room.falta'); cz.locator('[data-f="l"]').fill('3'); cz.locator('[data-f="c"]').fill('2,5')
    ok(pg.locator('.room.falta').count()==0,'medida digitada tira o vermelho')
    pg.screenshot(path='/home/claude/testes/voz-feito.png',full_page=False)
    av=pg.locator('[data-usar-dias]')
    ok(av.count()==1,'aviso de dias quando o número dito destoa da conta')
    sug=pg.evaluate("document.querySelector('[data-usar-dias]').textContent")
    av.click(); pg.wait_for_timeout(200)
    ok(pg.locator('[data-usar-dias]').count()==0 and pg.input_value('#dias') in sug,'Usar dias aplica a sugestão '+sug)
    # desfazer
    pg.click('#voz-desfazer'); pg.wait_for_timeout(500)
    ok(pg.locator('.room').count()==antes and pg.input_value('#c-nome')==nome0,'Desfazer volta como estava')
    # erro do servidor
    modo['v']='erro'
    pg.click('#voz-gravar'); pg.wait_for_timeout(2500); pg.click('#voz-enviar')
    pg.wait_for_function("document.querySelector('#voz').dataset.estado==='erro'",timeout=20000)
    ok('Não consegui ouvir' in pg.inner_text('#voz-erro-txt') and pg.is_visible('#voz-gravar'),'erro do servidor avisa e deixa gravar de novo')
    # recarregar mantém
    modo['v']='ok'; pg.click('#voz-gravar'); pg.wait_for_timeout(2500); pg.click('#voz-enviar'); pg.wait_for_function("document.querySelector('#voz').dataset.estado==='feito'",timeout=20000)
    pg.reload(); ok(pg.locator('.room, .room-mini').count()==3,'depois de recarregar os cômodos continuam')
    ok(est()=='feito' and 'Preenchi' in pg.inner_text('#voz-res') and not vis('#jeito'),'recarregar mantém o resumo e a separação')
    pg.click('#voz-todos'); pg.wait_for_timeout(300); ok(vis('#jeito') and vis('#c-nome') and not vis('#voz'),'Ver todos os campos mostra tudo')
    pg.evaluate("(()=>{const s=JSON.parse(localStorage.getItem('nabucha-proto-v5'));s.O.entrada='voz';localStorage.setItem('nabucha-proto-v5',JSON.stringify(s))})()"); pg.reload()
    pg.click('#voz-mais'); pg.wait_for_timeout(2500); pg.click('#voz-enviar'); pg.wait_for_function("document.querySelector('#voz').dataset.estado==='feito'",timeout=20000)
    ok(pg.locator('.room, .room-mini').count()==6,'Gravar mais soma cômodos ao orçamento de verdade')
    # sem rolagem lateral e alvo de toque
    ok(pg.evaluate('document.documentElement.scrollWidth<=390'),'sem rolagem lateral em 390px')
    ok(pg.evaluate("document.querySelector('#voz-mais').getBoundingClientRect().height>=44"),'botão com 44px ou mais')
    pg.screenshot(path='/home/claude/testes/voz-pronto.png')
    # passo 3: lucro com 'Outro'
    pg2=ctx.new_page(); pg2.on('pageerror',lambda e:erros.append(str(e)))
    pg2.route(re.compile(r'fonts\.g'),lambda r:r.abort())
    pg2.goto('http://localhost:8080/orcamento/'); pg2.evaluate('localStorage.clear()'); pg2.reload()
    pg2.click('#entrada [data-entrada="mao"]'); pg2.click('#next'); pg2.click('#next'); pg2.wait_for_timeout(300)
    ok(not pg2.is_visible('#lucro') and pg2.locator('#lucro-chips .chip.on').count()==1,'lucro: chips sem campo repetido')
    pg2.click('#lucro-chips [data-lucro="outro"]'); ok(pg2.is_visible('#lucro'),'Outro abre o campo do lucro')
    t0=pg2.inner_text('#total'); pg2.fill('#lucro','35'); pg2.wait_for_timeout(200); ok(pg2.inner_text('#total')!=t0,'lucro 35% muda o total')
    pg2.click('#lucro-chips [data-lucro="20"]'); ok(not pg2.is_visible('#lucro'),'voltar para 20% esconde o campo')
    # Meus preços: essencial visível, resto recolhido; digitar diária com vírgula
    pg2.click('#tab-cfg'); ok(pg2.is_visible('#cfg-diaria') and not pg2.is_visible('#cfg-svcs'),'Meus preços: essencial aberto, resto recolhido')
    pg2.fill('#cfg-diaria','1.234,56'); pg2.wait_for_timeout(200)
    ok(pg2.evaluate("JSON.parse(localStorage.getItem('nabucha-proto-v5')).C.diaria")=='1.234,56','diária com vírgula salva')
    # alvos de toque
    peq=pg2.evaluate('''[...document.querySelectorAll('button,.chip,summary,a')].filter(e=>e.offsetParent&&e.getBoundingClientRect().height<44).map(e=>(e.id||e.className||e.tagName)+':'+Math.round(e.getBoundingClientRect().height)).slice(0,8)''')
    ok(not peq,'Meus preços: todos os toques com 44px ou mais '+str(peq))
    pg2.click('#tab-orc'); pg2.wait_for_timeout(200)
    peq=pg2.evaluate('''[...document.querySelectorAll('button,.chip,summary,a')].filter(e=>e.offsetParent&&e.getBoundingClientRect().height<44).map(e=>(e.id||e.className||e.tagName)+':'+Math.round(e.getBoundingClientRect().height)).slice(0,8)''')
    ok(not peq,'Revisão: todos os toques com 44px ou mais '+str(peq))
    b.close()
ok(not erros,'sem erros de JavaScript '+str(erros[:3]))
print('TUDO OK' if not falhas else f'{len(falhas)} FALHA(S)')
