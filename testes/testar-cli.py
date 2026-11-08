import threading,http.server,functools,sys,os,json,time
from playwright.sync_api import sync_playwright
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*a):pass
srv=http.server.ThreadingHTTPServer(('127.0.0.1',8089),functools.partial(Q,directory='/home/claude/nabucha-site'))
threading.Thread(target=srv.serve_forever,daemon=True).start()
ok=True
def chk(n,c,x=''):
    global ok; print(('OK  ' if c else 'FALHOU ')+n,x); ok=ok and c
LS=lambda pg,k:pg.evaluate(f"JSON.parse(localStorage.getItem('{k}')||'[]')")
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx=b.new_context(viewport={'width':390,'height':844},accept_downloads=True); pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.goto('http://localhost:8089/orcamento/'); pg.evaluate('localStorage.clear()'); pg.reload(); pg.wait_for_timeout(800)
    pg.click('#entrada [data-entrada="mao"]'); pg.wait_for_timeout(300)
    pg.fill('#c-nome','Dona Marta'); pg.click('#rooms-card'); 
    pg.evaluate("document.querySelector('#c-whats').closest('details').open=true"); pg.fill('#c-whats','(37) 99999-1234'); pg.fill('#c-local','Centro')
    for i in range(3): pg.click('#next'); pg.wait_for_timeout(400)
    K=LS(pg,'nabucha-cli-v1'); chk('cliente cadastrado sozinho ao abrir a folha', len(K)==1 and K[0]['nome']=='Dona Marta' and K[0]['local']=='Centro', K and K[0]['nome'])
    pg.evaluate("document.querySelector('#wa').removeAttribute('target');document.querySelector('#wa').addEventListener('click',e=>e.preventDefault())")
    pg.click('#wa'); pg.click('#novo'); pg.wait_for_timeout(400)
    if pg.is_visible('#entrada'): pg.click('#entrada [data-entrada="mao"]'); pg.wait_for_timeout(300)
    chk('botão Escolher dos meus clientes aparece', pg.is_visible('#cli-escolher'))
    pg.click('#cli-escolher'); pg.wait_for_timeout(300); pg.click('[data-k-usar]'); pg.wait_for_timeout(300)
    chk('escolher cliente preenche o orçamento', pg.input_value('#c-nome')=='Dona Marta')
    pg.fill('#dias','3'); pg.wait_for_timeout(200)
    for i in range(3): pg.click('#next'); pg.wait_for_timeout(400)
    K=LS(pg,'nabucha-cli-v1'); H=LS(pg,'nabucha-hist-v1')
    chk('não duplica o cliente', len(K)==1, len(K)); chk('2 orçamentos ligados ao cliente', len([h for h in H if h['cliId']==K[0]['id']])==2)
    pg.click('#close'); pg.wait_for_timeout(300)
    pg.click('#cli-abrir'); pg.wait_for_timeout(300)
    chk('Meus clientes mostra 2 orçamentos', '2 orçamentos' in pg.inner_text('#cli-lista'))
    pg.click('#cli-novo'); pg.fill('#kf-nome','Seu Zé'); pg.fill('#kf-whats','37988887777'); pg.fill('#kf-obs','Prefere à tarde'); pg.click('#kf-ok'); pg.wait_for_timeout(300)
    chk('cadastrar cliente na mão', len(LS(pg,'nabucha-cli-v1'))==2 and 'Prefere à tarde' in pg.inner_text('#cli-lista'))
    pg.locator('[data-k-orc]').first.click(); pg.wait_for_timeout(400)
    chk('Novo orçamento para o cliente preenche o nome', pg.input_value('#c-nome')=='Seu Zé')
    pg.click('#cli-abrir'); pg.wait_for_timeout(300); pg.locator('[data-k-hist]').first.click(); pg.wait_for_timeout(300)
    chk('Orçamentos dele filtra a lista', pg.locator('#hist-lista .hi').count()==2 and 'Só de' in pg.inner_text('#hist-filtro-t'), (pg.locator('#hist-lista .hi').count(), pg.inner_text('#hist-filtro-t')))
    pg.locator('[data-h-st="fechado"]').first.click(); pg.wait_for_timeout(300)
    H=LS(pg,'nabucha-hist-v1'); chk('marcar Fechou', any(h.get('st')=='fechado' for h in H))
    chk('resumo do mês soma fechado', 'Fechados' in pg.inner_text('#resumo') and 'R$' in pg.inner_text('#resumo'), pg.inner_text('#resumo').replace('\n',' '))
    # cobrar resposta após 2 dias
    pg.evaluate("(()=>{const H=JSON.parse(localStorage.getItem('nabucha-hist-v1'));H.forEach(h=>{if(h.st!=='fechado'){h.st='enviado';h.enviado=true;h.enviadoEm=Date.now()-3*864e5}});localStorage.setItem('nabucha-hist-v1',JSON.stringify(H))})()")
    pg.reload(); pg.wait_for_timeout(600); pg.click('#hist-abrir'); pg.wait_for_timeout(300)
    chk('Cobrar resposta aparece após 2 dias', 'Cobrar resposta' in pg.inner_text('#hist-lista'))
    with pg.expect_download() as d: pg.click('#bk-salvar')
    path=d.value.path(); dados=json.load(open(path)); chk('cópia de segurança tem preços, orçamentos e clientes', dados['app']=='nabucha' and len(dados['H'])>=2 and len(dados['K'])==2)
    pg.evaluate('localStorage.clear()'); pg.reload(); pg.wait_for_timeout(600)
    pg.set_input_files('#bk-abrir', path); pg.wait_for_timeout(600)
    chk('restaurar cópia volta tudo', len(LS(pg,'nabucha-cli-v1'))==2 and len(LS(pg,'nabucha-hist-v1'))>=2)
    pg.click('#cli-abrir'); pg.wait_for_timeout(300); pg.screenshot(path='/tmp/cli.png')
    hs=pg.evaluate("[...document.querySelectorAll('#cli-wrap button,#cli-wrap a')].filter(b=>b.offsetParent).map(b=>(b.textContent||'').trim().slice(0,15)+':'+Math.round(b.getBoundingClientRect().height)).filter(x=>+x.split(':').pop()<44)")
    chk('toques com 44px ou mais', not hs, hs)
    chk('sem erros de JavaScript', not errs, errs)
    b.close()
print('TUDO OK' if ok else 'TEM FALHA')
