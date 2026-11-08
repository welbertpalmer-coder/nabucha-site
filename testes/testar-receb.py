import threading,http.server,functools,sys,os,json,datetime
from playwright.sync_api import sync_playwright
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8086),functools.partial(http.server.SimpleHTTPRequestHandler,directory='/home/claude/nabucha-site'))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=True
def chk(n,c,x=''):
    pass
def _x():pass
def chk(n,c,x=''):
    global ok; print(('OK  ' if c else 'FALHOU ')+n,x); ok=ok and c
hoje=datetime.date.today()
def d(n): return (hoje+datetime.timedelta(days=n)).isoformat()
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx=b.new_context(viewport={'width':390,'height':844}); pg=ctx.new_page(); errs=[]
    _it=pg.inner_text; pg.inner_text=lambda sel:_it(sel).replace('\xa0',' ')
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://localhost:8086/orcamento/'); pg.evaluate('localStorage.clear()'); pg.reload(); pg.wait_for_timeout(600)
    O0=pg.evaluate("JSON.parse(localStorage.getItem('nabucha-proto-v5')||'null')")
    O0=O0 and O0['O']
    # dois orçamentos enviados (um de 8.000 da Dona Marta) + um antigo já fechado
    H=[{'id':'a1','cliId':None,'quando':0,'enviadoEm':0,'cliente':'Dona Marta Silva','local':'Centro','whats':'37999998888','total':8000,'st':'enviado','enviado':True,'num':1,'o':{'pay':['Pix','50% de entrada'],'cliente':{'nome':'Dona Marta Silva'}}},
       {'id':'a2','cliId':None,'quando':0,'enviadoEm':0,'cliente':'Seu Zé','local':'','whats':'','total':3000,'st':'fechado','enviado':True,'num':2,'o':{'pay':['Pix'],'cliente':{'nome':'Seu Zé'}},
        'pag':{'acomp':True,'valor':3000,'tipo':'entrada','ent':1000,'entD':d(-20),'fim':d(-3),'n':4,'parc':[{'d':d(-20),'v':1000},{'d':d(-3),'v':2000}],'recs':[{'id':'r0','d':d(-20),'v':1000,'f':'Pix'}]}}]
    import time,copy; now=int(time.time()*1000)
    for h,pay in zip(H,[['Pix','50% de entrada'],['Pix']]):
        o=copy.deepcopy(O0); o['cliente']={'nome':h['cliente'],'whats':h['whats'],'local':h['local']}; o['pay']=pay; o['id']=h['id']; h['o']=o
    for h in H: h['quando']=now; h['enviadoEm']=now
    pg.evaluate("h=>localStorage.setItem('nabucha-hist-v1',JSON.stringify(h))",H); pg.reload(); pg.wait_for_timeout(800)
    chk('linha Meus mostra atrasado do Seu Zé', 'atrasado' in pg.inner_text('#hist-row'), pg.inner_text('#hist-row'))
    chk('botão Recebimentos aparece', pg.is_visible('#rec-abrir'))
    pg.click('#hist-abrir'); pg.wait_for_timeout(300)
    chk('item fechado mostra barra e falta', 'falta' in pg.inner_text('#hist-lista'))
    # Dona Marta fechou
    pg.click('[data-h-st="fechado"][data-id="a1"]'); pg.wait_for_timeout(300)
    chk('ao fechar pergunta se quer acompanhar', pg.is_visible('#pag-wrap') and 'Quer acompanhar' in pg.inner_text('#pag-corpo'))
    pg.click('[data-pg="sim"]'); pg.wait_for_timeout(200)
    chk('valor combinado já vem 8.000', pg.input_value('#pc-valor')=='8000', pg.input_value('#pc-valor'))
    chk('jeito sugerido pelo orçamento (50% de entrada)', 'on' in pg.get_attribute('[data-pc-tipo="entrada"]','class'))
    pg.click('[data-pc-tipo="semana"]'); pg.wait_for_timeout(200)
    pg.fill('#pc-valor','7.500'); pg.fill('#pc-ent','1.500'); pg.fill('#pc-n','4'); pg.fill('#pc-ini',d(7)); pg.fill('#pc-entD',d(-14)); pg.wait_for_timeout(200)
    prev=pg.inner_text('#pc-prev')
    chk('prévia: entrada + 4 semanas de 1.500', prev.count('1.500,00')==5, prev.replace('\n',' | '))
    pg.click('[data-pg="salvar"]'); pg.wait_for_timeout(300)
    txt=pg.inner_text('#pag-corpo')
    chk('entrada vencida sem pagamento aparece atrasada', 'atrasado' in txt.lower() and 'Cobrar no WhatsApp' in txt)
    href=pg.get_attribute('[data-cobrar]','href')
    chk('cobrança vai para o WhatsApp da cliente com valor', 'wa.me/5537999998888' in href and '1.500' in __import__('urllib.parse').parse.unquote(href))
    pg.click('[data-pg="receber"]'); pg.wait_for_timeout(200)
    chk('valor sugerido = parcela em aberto', pg.input_value('#pr-valor')=='1500', pg.input_value('#pr-valor'))
    pg.fill('#pr-valor','2000'); pg.click('[data-pr-forma="Dinheiro"]'); pg.click('[data-pg="rec-salvar"]'); pg.wait_for_timeout(300)
    txt=pg.inner_text('#pag-corpo')
    chk('recebeu 2.000: falta 5.500', 'R$ 5.500,00' in txt, '')
    chk('sem atraso depois de pagar', 'Cobrar no WhatsApp' not in txt)
    chk('1ª semana ficou parcial (falta 1.000)', 'Falta R$ 1.000' in txt)
    pg.screenshot(path='/tmp/pag.png',full_page=True)
    # apagar pagamento pede 2 toques
    pg.locator('[data-pr-del]').first.click(); pg.wait_for_timeout(100)
    chk('apagar pede 2º toque', 'Toque de novo' in pg.inner_text('#pag-corpo'))
    pg.locator('[data-pr-del]').first.click(); pg.wait_for_timeout(200)
    chk('apagou: falta 7.500 de novo', 'R$ 7.500,00' in pg.inner_text('#pag-corpo'))
    pg.click('[data-pg="receber"]'); pg.fill('#pr-valor','1.500,00'); pg.click('[data-pg="rec-salvar"]'); pg.wait_for_timeout(200)
    pg.click('#pag-fechar'); pg.wait_for_timeout(200)
    # tela Recebimentos
    pg.click('#hist-rec'); pg.wait_for_timeout(300)
    t=pg.inner_text('#rec-corpo')
    chk('Recebimentos: falta receber 8.000 (6.000 + 2.000)', 'R$ 8.000' in t, t[:120].replace('\n',' | '))
    chk('Recebimentos: atrasado 2.000 (Seu Zé)', 'R$ 2.000' in t)
    chk('gráfico por mês desenhado', pg.locator('#ch-mes svg rect').count()>=2)
    chk('Seu Zé (atrasado) vem primeiro', pg.locator('.sv').first.inner_text().startswith('Seu'))
    pg.screenshot(path='/tmp/rec.png',full_page=True)
    pg.click('[data-cheia="ch-mes"]'); pg.wait_for_timeout(200)
    bb=pg.locator('#ch-mes').bounding_box()
    chk('tela cheia ocupa a tela', bb['width']>=389 and bb['height']>=840, bb)
    pg.screenshot(path='/tmp/cheia.png')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    chk('Esc sai da tela cheia e mantém Recebimentos', not pg.locator('.chart.cheia').count() and pg.is_visible('#rec-wrap'))
    pg.locator('.sv').first.click(); pg.wait_for_timeout(200)
    chk('tocar no serviço abre o pagamento dele', pg.is_visible('#pag-wrap') and 'Seu Zé' in pg.inner_text('#pag-sub'))
    pg.click('#pag-fechar')
    # celular deitado
    pg.set_viewport_size({'width':844,'height':390}); pg.wait_for_timeout(300)
    g=pg.evaluate("getComputedStyle(document.querySelector('.rec-grid')).display")
    chk('deitado: gráficos lado a lado', g=='grid', g)
    pg.screenshot(path='/tmp/deitado.png')
    pg.set_viewport_size({'width':390,'height':844})
    pg.click('#rec-fechar'); pg.wait_for_timeout(200)
    # o pagamento sobrevive a reabrir e editar o orçamento (guardar)
    pg.click('[data-h-abrir="a2"]'); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('#next').click()"); pg.wait_for_timeout(400)
    for i in range(3):
        if pg.is_visible('#sheet-wrap'): break
        pg.evaluate("document.querySelector('#next').click()"); pg.wait_for_timeout(400)
    Hs=pg.evaluate("JSON.parse(localStorage.getItem('nabucha-hist-v1'))")
    z=[h for h in Hs if h['id']=='a2'][0]
    chk('editar o orçamento não perde o pagamento', z.get('pag') and len(z['pag']['recs'])==1)
    # limite de 30 não derruba quem tem dinheiro a receber
    r=pg.evaluate("""()=>{const H=JSON.parse(localStorage.getItem('nabucha-hist-v1'));for(let k=0;k<40;k++)H.unshift({id:'x'+k,quando:Date.now(),cliente:'C'+k,total:100,st:'enviado',enviado:true,o:Object.assign(JSON.parse(JSON.stringify(H[H.length-1].o)),{id:'x'+k})});localStorage.setItem('nabucha-hist-v1',JSON.stringify(H));return H.length}""")
    pg.reload(); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('#hist-abrir').click()"); pg.wait_for_timeout(200); pg.evaluate("document.querySelector('[data-h-dup]').click()"); pg.wait_for_timeout(400)
    for i in range(4):
        if pg.is_visible('#sheet-wrap'): break
        pg.evaluate("document.querySelector('#next').click()"); pg.wait_for_timeout(400)
    Hs=pg.evaluate("JSON.parse(localStorage.getItem('nabucha-hist-v1'))")
    ids=[h['id'] for h in Hs]
    chk('lista volta a 30 e mantém os com pagamento em aberto', len(Hs)==30 and 'a1' in ids and 'a2' in ids, len(Hs))
    hs=pg.evaluate("[...document.querySelectorAll('#pag-wrap button,#rec-wrap button')].filter(b=>b.offsetParent).map(b=>b.getBoundingClientRect().height).filter(h=>h<44)")
    chk('sem erros de JavaScript', not errs, errs)
    b.close()
print('TUDO OK' if ok else 'TEM FALHA')
