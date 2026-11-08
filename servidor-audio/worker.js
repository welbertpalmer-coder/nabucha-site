// Na Bucha — servidor do áudio (Cloudflare Worker, plano grátis)
// Recebe o áudio do orçamento (WAV 16 kHz), transcreve com Whisper e extrai os campos com Llama.
// Nada é guardado: o áudio e o texto só passam por aqui e voltam para o celular.
// Rota /registro: guarda uso anônimo, erros e comentários do site no banco D1 (binding DB).
// Rota /registro/relatorio?k=CHAVE: resumo para o Claude ler (CHAVE_RELATORIO é um segredo do Worker).

const ORIGENS = ['https://nabucha.com.br', 'https://www.nabucha.com.br', 'http://localhost:8080'];
const MAX_BYTES = 6 * 1024 * 1024; // ~3 min de WAV 16 kHz mono

const SCHEMA = {
  type: 'object',
  properties: {
    cliente_nome: { type: 'string' },
    cliente_local: { type: 'string' },
    modo: { type: 'string', enum: ['', 'custo', 'diaria', 'm2', 'fechado'] },
    dias: { type: ['number', 'null'] },
    ajudantes: { type: ['integer', 'null'] },
    comodos: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          nome: { type: 'string' },
          largura: { type: ['number', 'null'] },
          comprimento: { type: ['number', 'null'] },
          pe_direito: { type: ['number', 'null'] },
          area_paredes: { type: ['number', 'null'] },
          area_teto: { type: ['number', 'null'] },
          pintar_teto: { type: ['boolean', 'null'] },
          portas: { type: ['integer', 'null'] },
          janelas: { type: ['integer', 'null'] }
        },
        required: ['nome', 'largura', 'comprimento', 'pe_direito', 'area_paredes', 'area_teto', 'pintar_teto', 'portas', 'janelas']
      }
    },
    situacoes: { type: 'array', items: { type: 'string', enum: ['repintura', 'cor', 'forte', 'novo', 'esfarela'] } },
    reparos: { type: 'array', items: { type: 'string', enum: ['mofo', 'furos', 'trinca', 'descasca', 'infil'] } },
    acabamento: { type: 'string', enum: ['', 'fosco', 'acet', 'semi', 'brilho'] },
    massa_corrida: { type: 'boolean' },
    textura: { type: 'boolean' },
    prazo: { type: 'string' },
    obs: { type: 'string' }
  },
  required: ['cliente_nome', 'cliente_local', 'modo', 'dias', 'ajudantes', 'comodos', 'situacoes', 'reparos', 'acabamento', 'massa_corrida', 'textura', 'prazo', 'obs']
};

const SISTEMA = `Você recebe a transcrição de um áudio de um pintor brasileiro descrevendo um serviço para orçar.
Extraia os dados e responda SÓ com JSON no formato pedido. Regras:
- Medidas em metros, como número (ponto decimal). "três e meio" = 3.5; "3 e 20" ou "três vinte" = 3.2; "2,60" = 2.6; "350" falando de cômodo = 3.5.
- "quarto 3 por 4" = largura 3, comprimento 4. Se ele der a área em m² ("40 metros de parede"), use area_paredes/area_teto e deixe largura e comprimento null.
- Um item em "comodos" para cada cômodo ou ambiente citado (sala, quarto, cozinha, banheiro, área externa, muro, fachada...). Use o nome que ele usou ("quarto da menina"). Não invente medida: o que ele não disse fica null.
- pintar_teto: true se disse que pinta o teto, false se disse que não, null se não falou.
- situacoes: repintura (mesma cor), cor (mudar de cor), forte (cor forte/escura), novo (reboco novo), esfarela (parede esfarelando, caiada, pó).
- reparos: mofo, furos (furos de parafuso, buchas), trinca (trinca, rachadura), descasca (descascando, bolhas), infil (infiltração, umidade).
- acabamento: fosco, acet (acetinado), semi (semibrilho), brilho. Vazio se não falou.
- massa_corrida true se falou em massa corrida ou emassamento; textura true se falou em textura ou grafiato.
- modo: diaria se ele cobra por dia/diária; m2 se cobra por metro; fechado se falou de preço fechado/empreitada; custo se falou em custo mais lucro; vazio se não falou.
- dias: quantos dias de serviço ele disse (número) ou null. ajudantes: quantos ajudantes ou null.
- cliente_nome: nome do cliente se citado ("dona Marta"). cliente_local: bairro ou endereço se citado. Nunca coloque nome de cômodo como cliente.
- prazo: prazo dito em texto curto ou vazio. obs: qualquer outra informação útil ao orçamento, curta, ou vazio.`;

function cors(origin) {
  return {
    'Access-Control-Allow-Origin': ORIGENS.includes(origin) ? origin : ORIGENS[0],
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin'
  };
}
const json = (obj, status, origin) =>
  new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json; charset=utf-8', ...cors(origin) } });

function b64(buf) {
  const bytes = new Uint8Array(buf);
  let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

function pegarJson(txt) {
  if (txt && typeof txt === 'object') return txt;
  const m = String(txt || '').match(/\{[\s\S]*\}/);
  return m ? JSON.parse(m[0]) : null;
}

// ---------- REGISTRO DE USO, ERROS E COMENTÁRIOS ----------
const TIPOS = ['ev', 'erro', 'coment'];
const corta = (v, n) => (v == null ? '' : String(v)).slice(0, n);
async function tabela(db) {
  await db.prepare(`CREATE TABLE IF NOT EXISTS registros (
    id INTEGER PRIMARY KEY AUTOINCREMENT, quando TEXT NOT NULL, tipo TEXT NOT NULL, nome TEXT, pagina TEXT,
    detalhe TEXT, nota INTEGER, contato TEXT, vid TEXT, sid TEXT, versao TEXT, aparelho TEXT)`).run();
}
async function registrar(req, env, origin) {
  if (!env.DB) return json({ erro: 'Banco não ligado' }, 503, origin);
  const txt = await req.text();
  if (txt.length > 4000) return json({ erro: 'Grande demais' }, 413, origin);
  let lista;
  try { lista = JSON.parse(txt); } catch (e) { return json({ erro: 'Formato inválido' }, 400, origin); }
  if (!Array.isArray(lista)) lista = [lista];
  lista = lista.filter(r => r && TIPOS.includes(r.t)).slice(0, 20);
  if (!lista.length) return json({ ok: true, n: 0 }, 200, origin);
  await tabela(env.DB);
  const vid = corta(lista[0].vid, 12);
  // anti-abuso: no máximo 120 registros por visitante a cada 10 minutos
  const q = await env.DB.prepare(`SELECT COUNT(*) AS n FROM registros WHERE vid = ? AND quando > datetime('now','-10 minutes')`).bind(vid).first();
  if (q && q.n > 120) return json({ ok: true, n: 0, limite: true }, 200, origin);
  const agora = new Date().toISOString().replace('T', ' ').slice(0, 19);
  const ins = env.DB.prepare(`INSERT INTO registros (quando,tipo,nome,pagina,detalhe,nota,contato,vid,sid,versao,aparelho) VALUES (?,?,?,?,?,?,?,?,?,?,?)`);
  await env.DB.batch(lista.map(r => {
    const nota = Number.isInteger(r.nota) && r.nota >= 1 && r.nota <= 5 ? r.nota : null;
    return ins.bind(agora, r.t, corta(r.n, 40), corta(r.p, 40), corta(r.d, r.t === 'coment' ? 1000 : 300), nota,
      r.t === 'coment' ? corta(r.contato, 40) : '', vid, corta(r.sid, 10), corta(r.v, 20), corta(r.a, 60));
  }));
  // limpeza: apaga o que tiver mais de 180 dias (de vez em quando)
  if (Math.random() < 0.02) await env.DB.prepare(`DELETE FROM registros WHERE quando < datetime('now','-180 days')`).run();
  return json({ ok: true, n: lista.length }, 200, origin);
}
async function relatorio(url, env, origin) {
  if (!env.DB || !env.CHAVE_RELATORIO || url.searchParams.get('k') !== env.CHAVE_RELATORIO) return json({ erro: 'Sem acesso' }, 403, origin);
  await tabela(env.DB);
  const dias = Math.min(180, Math.max(1, parseInt(url.searchParams.get('dias') || '7', 10) || 7));
  const desde = `datetime('now','-${dias} days')`;
  const tudo = async sql => (await env.DB.prepare(sql).all()).results;
  const funil = await tudo(`SELECT nome, detalhe, pagina, COUNT(DISTINCT vid) AS pessoas, COUNT(*) AS vezes FROM registros WHERE tipo='ev' AND quando > ${desde} GROUP BY nome, detalhe, pagina ORDER BY pagina, pessoas DESC`);
  const porDia = await tudo(`SELECT substr(quando,1,10) AS dia, COUNT(DISTINCT vid) AS pessoas FROM registros WHERE quando > ${desde} GROUP BY dia ORDER BY dia`);
  const erros = await tudo(`SELECT nome, pagina, detalhe, COUNT(*) AS vezes, COUNT(DISTINCT vid) AS pessoas, MAX(quando) AS ultimo, MAX(aparelho) AS aparelho FROM registros WHERE tipo='erro' AND quando > ${desde} GROUP BY nome, pagina, detalhe ORDER BY vezes DESC LIMIT 50`);
  const comentarios = await tudo(`SELECT quando, pagina, nome, detalhe, nota, contato, aparelho FROM registros WHERE tipo='coment' AND quando > ${desde} ORDER BY quando DESC LIMIT 100`);
  const aparelhos = await tudo(`SELECT aparelho, COUNT(DISTINCT vid) AS pessoas FROM registros WHERE quando > ${desde} GROUP BY aparelho ORDER BY pessoas DESC LIMIT 15`);
  return json({ dias, gerado: new Date().toISOString(), por_dia: porDia, funil, erros, comentarios, aparelhos }, 200, origin);
}

export default {
  async fetch(req, env) {
    const origin = req.headers.get('Origin') || '';
    const url = new URL(req.url);
    if (req.method === 'OPTIONS') return new Response(null, { headers: cors(origin) });
    if (url.pathname === '/registro/relatorio' && req.method === 'GET') return relatorio(url, env, origin);
    if (url.pathname === '/registro') {
      if (req.method !== 'POST') return json({ erro: 'Método não aceito' }, 405, origin);
      if (!ORIGENS.includes(origin)) return json({ erro: 'Origem não autorizada' }, 403, origin);
      try { return await registrar(req, env, origin); }
      catch (e) { return json({ erro: 'Falha ao guardar', detalhe: String(e).slice(0, 200) }, 500, origin); }
    }
    if (req.method === 'GET') return json({ ok: true, servico: 'nabucha-audio' }, 200, origin);
    if (req.method !== 'POST') return json({ erro: 'Método não aceito' }, 405, origin);
    if (!ORIGENS.includes(origin)) return json({ erro: 'Origem não autorizada' }, 403, origin);

    const buf = await req.arrayBuffer();
    if (!buf.byteLength) return json({ erro: 'Áudio vazio' }, 400, origin);
    if (buf.byteLength > MAX_BYTES) return json({ erro: 'Áudio longo demais (máx. ~3 min)' }, 413, origin);

    let texto = '';
    try {
      const t = await env.AI.run('@cf/openai/whisper-large-v3-turbo', {
        audio: b64(buf), language: 'pt', vad_filter: true,
        initial_prompt: 'Orçamento de pintura: quarto, sala, cozinha, pé-direito, demãos, massa corrida, textura, selador, mofo, trinca, diária.'
      });
      texto = (t && t.text || '').trim();
    } catch (e) {
      return json({ erro: 'Não consegui ouvir o áudio agora', detalhe: String(e).slice(0, 200) }, 502, origin);
    }
    if (!texto) return json({ erro: 'Não entendi nada no áudio. Fale mais perto do celular.' }, 422, origin);

    let dados = null;
    try {
      const r = await env.AI.run('@cf/meta/llama-3.3-70b-instruct-fp8-fast', {
        messages: [{ role: 'system', content: SISTEMA }, { role: 'user', content: texto }],
        response_format: { type: 'json_schema', json_schema: SCHEMA },
        max_tokens: 1200, temperature: 0
      });
      dados = pegarJson(r && r.response);
    } catch (e) {
      return json({ texto, erro: 'Ouvi o áudio, mas não consegui organizar os dados', detalhe: String(e).slice(0, 200) }, 502, origin);
    }
    if (!dados) return json({ texto, erro: 'Ouvi o áudio, mas não consegui organizar os dados' }, 502, origin);
    return json({ texto, dados }, 200, origin);
  }
};
