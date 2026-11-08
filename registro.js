/* Na Bucha — registro anônimo de uso, erros e comentários.
   Manda para o servidor do Na Bucha (Cloudflare) só: o que foi usado (passos), erros e comentários.
   Nunca manda nome de cliente, telefone de cliente, medidas, valores nem o áudio.
   Para desligar tudo: apague a linha <script src="/registro.js"> das páginas. */
(function () {
  const URL_REG = 'https://hello-world-black-sun-acbf.contato-nabucha.workers.dev/registro';
  const VERSAO = '2026-11-08';
  const PEND = 'nb-coment-pend';
  const pagina = location.pathname.indexOf('orcamento') >= 0 ? 'orcamento' : (location.pathname.indexOf('privacidade') >= 0 ? 'privacidade' : 'inicio');
  const local = /^(localhost|127\.0\.0\.1)$/.test(location.hostname);

  let vid = '?';
  try { vid = localStorage.getItem('nb-vid'); if (!vid) { vid = Math.random().toString(36).slice(2, 10); localStorage.setItem('nb-vid', vid); } } catch (e) {}
  const sid = Math.random().toString(36).slice(2, 8);

  function aparelho() {
    const u = navigator.userAgent;
    const so = /Android/i.test(u) ? 'Android' : /iPhone|iPad/i.test(u) ? 'iPhone' : /Windows/i.test(u) ? 'Windows' : /Mac/i.test(u) ? 'Mac' : 'outro';
    const nav = /SamsungBrowser/i.test(u) ? 'Samsung' : /Edg\//i.test(u) ? 'Edge' : /Chrome|CriOS/i.test(u) ? 'Chrome' : /Firefox|FxiOS/i.test(u) ? 'Firefox' : /Safari/i.test(u) ? 'Safari' : 'outro';
    const inApp = /Instagram|FBAN|FBAV/i.test(u) ? ' (app Insta/Face)' : '';
    return so + ' · ' + nav + inApp + ' · ' + Math.round(screen.width) + 'px';
  }
  const AP = aparelho();

  let fila = [];
  const jaFoi = new Set();
  const base = () => ({ vid: vid, sid: sid, v: VERSAO, a: AP, p: pagina });

  function despachar(usarBeacon) {
    if (!fila.length) return;
    const corpo = JSON.stringify(fila.splice(0, 20));
    if (local) { console.log('[registro]', corpo); return; }
    try {
      if (usarBeacon && navigator.sendBeacon && navigator.sendBeacon(URL_REG, new Blob([corpo], { type: 'text/plain' }))) return;
    } catch (e) {}
    fetch(URL_REG, { method: 'POST', body: corpo, keepalive: true, headers: { 'Content-Type': 'text/plain' } }).catch(function () {});
  }
  setInterval(function () { despachar(false); }, 6000);
  addEventListener('pagehide', function () { despachar(true); });
  document.addEventListener('visibilitychange', function () { if (document.visibilityState === 'hidden') despachar(true); });

  // Evento de uso. "uma" = conta só uma vez por visita.
  function ev(nome, detalhe, uma) {
    const k = nome + '|' + (detalhe || '');
    if (uma && jaFoi.has(k)) return;
    jaFoi.add(k);
    fila.push(Object.assign(base(), { t: 'ev', n: nome, d: detalhe || '' }));
    if (fila.length >= 10) despachar(false);
  }
  // Erro: algo quebrou ou deu errado para a pessoa.
  let nErros = 0;
  function erro(nome, detalhe) {
    if (++nErros > 30) return;
    const d = String(detalhe || '').replace(/\d{8,}/g, '#').slice(0, 300); // tira números longos (telefone)
    fila.push(Object.assign(base(), { t: 'erro', n: nome, d: d }));
    despachar(false);
  }
  addEventListener('error', function (e) {
    if (e.target && e.target !== window && e.target.tagName) { erro('recurso-nao-carregou', e.target.tagName + ' ' + (e.target.src || e.target.href || '')); return; }
    erro('erro-js', (e.message || '') + ' @' + String(e.filename || '').split('/').pop() + ':' + (e.lineno || '') + ':' + (e.colno || ''));
  }, true);
  addEventListener('unhandledrejection', function (e) { erro('erro-js-promessa', e.reason && (e.reason.message || String(e.reason))); });

  // Comentário: precisa chegar. Se cair a internet, guarda e tenta de novo depois.
  async function mandarComent(item) {
    if (local) { console.log('[comentario]', item); return true; }
    try {
      const r = await fetch(URL_REG, { method: 'POST', body: JSON.stringify([item]), headers: { 'Content-Type': 'text/plain' } });
      return r.ok;
    } catch (e) { return false; }
  }
  async function reenviar() {
    let p = [];
    try { p = JSON.parse(localStorage.getItem(PEND) || '[]') || []; } catch (e) {}
    if (!p.length) return;
    const sobrou = [];
    for (const it of p) if (!(await mandarComent(it))) sobrou.push(it);
    try { sobrou.length ? localStorage.setItem(PEND, JSON.stringify(sobrou)) : localStorage.removeItem(PEND); } catch (e) {}
  }
  setTimeout(reenviar, 3000);

  async function comentar(texto, nota, contato, origem) {
    const item = Object.assign(base(), { t: 'coment', n: origem || 'caixa', d: String(texto || '').slice(0, 1000), nota: nota || null, contato: String(contato || '').slice(0, 40) });
    if (await mandarComent(item)) return true;
    try { const p = JSON.parse(localStorage.getItem(PEND) || '[]') || []; p.push(item); localStorage.setItem(PEND, JSON.stringify(p.slice(-10))); } catch (e) {}
    return false;
  }

  // ---------- Caixa "Sugestão ou problema?" com a Capi ----------
  const css = `
.nbc-wrap{position:fixed;inset:0;background:rgba(11,16,48,.72);z-index:40;display:flex;align-items:flex-end;justify-content:center;padding:12px;padding-bottom:calc(12px + env(safe-area-inset-bottom,0px))}
.nbc{background:var(--surface,#fff);color:var(--ink,#0B1030);border-radius:20px;padding:18px 16px 16px;width:100%;max-width:480px;display:flex;flex-direction:column;gap:12px;font-family:var(--body,system-ui,sans-serif);max-height:calc(100vh - 24px);overflow-y:auto}
@media (prefers-reduced-motion:no-preference){.nbc{animation:nbcUp .22s ease-out}@keyframes nbcUp{from{transform:translateY(18px);opacity:.5}}}
.nbc-cab{display:flex;gap:12px;align-items:center}
.nbc-cab img{width:64px;height:64px;object-fit:contain;flex:none}
.nbc h2{font-family:var(--display,inherit);font-size:18px;margin:0;line-height:1.2}
.nbc p{margin:2px 0 0;font-size:14px;color:var(--muted,#565B75)}
.nbc textarea,.nbc input{font:inherit;font-size:16px;color:var(--ink,#0B1030);background:var(--bg,#F4F1EA);border:1.5px solid var(--line,#DDD8CB);border-radius:12px;padding:11px 12px;width:100%;box-sizing:border-box}
.nbc textarea{min-height:110px;resize:vertical}
.nbc label{font-size:14px;font-weight:600;display:flex;flex-direction:column;gap:6px}
.nbc-notas{display:flex;gap:6px}
.nbc-notas button{flex:1;min-height:48px;border-radius:12px;border:1.5px solid var(--line,#DDD8CB);background:var(--bg,#F4F1EA);color:var(--ink,#0B1030);font:inherit;font-size:20px;cursor:pointer}
.nbc-notas button[aria-pressed="true"]{border-color:var(--accent,#1F3BFF);background:var(--soft,#E9EBFF)}
.nbc-acoes{display:flex;gap:8px}
.nbc-acoes button{min-height:52px;border-radius:14px;font:inherit;font-weight:700;font-size:16px;cursor:pointer}
.nbc-env{flex:1;background:var(--btn,#1F3BFF);color:var(--btn-ink,#fff);border:none}
.nbc-env:disabled{opacity:.5}
.nbc-fec{background:none;border:1.5px solid var(--line,#DDD8CB);color:var(--ink,#0B1030);padding:0 16px}
.nbc-msg{font-size:14px;margin:0;color:#C2410C;font-weight:600}
.nbc-ok{text-align:center;display:flex;flex-direction:column;align-items:center;gap:8px;padding:8px 0}
.nbc-ok img{width:110px;height:110px;object-fit:contain}
.nbc-link{font:inherit;font-size:14px;font-weight:600;color:var(--muted,#565B75);background:none;border:none;text-decoration:underline;text-underline-offset:3px;cursor:pointer;min-height:44px;display:inline-flex;align-items:center;gap:6px;padding:0 4px}
`;
  let estilo = false;
  function abrir(origem, comNota) {
    if (!estilo) { const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s); estilo = true; }
    ev('coment-abriu', origem);
    const antes = document.activeElement;
    const ov = document.createElement('div');
    ov.className = 'nbc-wrap';
    ov.innerHTML = `<div class="nbc" role="dialog" aria-modal="true" aria-labelledby="nbc-t">
  <div class="nbc-cab"><img src="/img/capi/capi-pensando.webp" alt="Capi, a capivara do Na Bucha, pensando"><div><h2 id="nbc-t">${comNota ? 'O que achou?' : 'Sugestão ou problema?'}</h2><p>Conta pra gente. Quem lê é o pessoal que faz o Na Bucha.</p></div></div>
  ${comNota ? '<div class="nbc-notas" role="group" aria-label="Nota de 1 a 5">' + ['😞', '🙁', '😐', '🙂', '😄'].map((e, i) => `<button type="button" data-n="${i + 1}" aria-pressed="false" aria-label="Nota ${i + 1}">${e}</button>`).join('') + '</div>' : ''}
  <label>O que aconteceu ou o que podia melhorar?<textarea id="nbc-txt" maxlength="1000" placeholder="Ex.: o áudio não preencheu a medida do teto"></textarea></label>
  <label>Seu WhatsApp, se quiser resposta (opcional)<input id="nbc-zap" inputmode="tel" maxlength="20" autocomplete="tel" placeholder="(37) 9 9999-9999"></label>
  <p class="nbc-msg" id="nbc-msg" hidden></p>
  <div class="nbc-acoes"><button type="button" class="nbc-fec" id="nbc-fec">Fechar</button><button type="button" class="nbc-env" id="nbc-env">Enviar</button></div>
  <p style="font-size:12px;margin:0">Não escreva dados do seu cliente. <a href="/privacidade.html" target="_blank" rel="noopener">Privacidade</a></p>
</div>`;
    document.body.appendChild(ov);
    const ovAntes = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const q = s => ov.querySelector(s);
    let nota = null;
    const fechar = () => { ov.remove(); document.body.style.overflow = ovAntes; document.removeEventListener('keydown', esc); if (antes && antes.focus) antes.focus({ preventScroll: true }); };
    const esc = e => { if (e.key === 'Escape') fechar(); };
    document.addEventListener('keydown', esc);
    ov.addEventListener('click', e => { if (e.target === ov) fechar(); });
    q('#nbc-fec').addEventListener('click', fechar);
    ov.querySelectorAll('[data-n]').forEach(b => b.addEventListener('click', () => {
      nota = +b.dataset.n; ov.querySelectorAll('[data-n]').forEach(x => x.setAttribute('aria-pressed', x === b ? 'true' : 'false'));
    }));
    q('#nbc-env').addEventListener('click', async () => {
      const txt = q('#nbc-txt').value.trim(), zap = q('#nbc-zap').value.trim();
      if (!txt && !nota) { const m = q('#nbc-msg'); m.textContent = comNota ? 'Escolha uma carinha ou escreva algo.' : 'Escreva o que aconteceu.'; m.hidden = false; q('#nbc-txt').focus(); return; }
      const b = q('#nbc-env'); b.disabled = true; b.textContent = 'Enviando…';
      const ok = await comentar(txt, nota, zap, origem);
      q('.nbc').innerHTML = `<div class="nbc-ok"><img src="/img/capi/capi-feliz.webp" alt="Capi, a capivara do Na Bucha, comemorando"><h2>${ok ? 'Recebido. Valeu!' : 'Guardado no seu celular'}</h2><p>${ok ? 'A gente lê tudo e usa para melhorar.' : 'Sem internet agora. Mandamos sozinho quando ela voltar.'}</p><button type="button" class="nbc-env" style="width:100%;min-height:52px;border-radius:14px;font:inherit;font-weight:700" id="nbc-ok">Fechar</button></div>`;
      q('#nbc-ok').addEventListener('click', fechar); q('#nbc-ok').focus();
    });
    setTimeout(() => { const f = comNota ? ov.querySelector('[data-n]') : q('#nbc-txt'); if (f) f.focus({ preventScroll: true }); }, 50);
  }
  document.addEventListener('click', e => { const b = e.target.closest('[data-coment]'); if (b) { e.preventDefault(); abrir(b.dataset.coment || 'caixa', b.hasAttribute('data-coment-nota')); } });

  window.nbReg = { ev: ev, erro: erro, abrir: abrir };
  ev('abriu', pagina, true);
})();
