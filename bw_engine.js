/* Motor de cálculo do Tracking BW — mesma lógica do pipeline em Python, rodando no navegador. */
(function (root) {
  'use strict';

  // ---------- leitura de CSV ----------
  const num = (s) => {
    if (s == null) return NaN;
    const t = String(s).trim().replace(/\./g, '').replace(',', '.');
    if (t === '') return NaN;
    const n = Number(t);
    return isNaN(n) ? NaN : n;
  };
  const stripZeros = (s) => String(s).trim().replace(/^0+/, '');

  function parseCSV(text) {
    // ; separado, aspas opcionais
    const rows = [];
    let row = [], cur = '', q = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) {
        if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else q = false; }
        else cur += c;
      } else if (c === '"') q = true;
      else if (c === ';') { row.push(cur); cur = ''; }
      else if (c === '\n') { row.push(cur); rows.push(row); row = []; cur = ''; }
      else if (c === '\r') { /* ignora */ }
      else cur += c;
    }
    if (cur !== '' || row.length) { row.push(cur); rows.push(row); }
    return rows.filter((r) => r.length > 1 || (r[0] || '').trim() !== '');
  }

  // relatório ABC de venda: Quebra (loja) ; Quebra2 (data) ; Código ; Descrição ; Quantidade ; Faturamento ; ...
  function parseVendas(text) {
    const rows = parseCSV(text);
    const head = rows.shift() || [];
    if (head.length < 6 || !/quebra/i.test(head[0]) || !/quebra/i.test(head[1] || '')) {
      throw new Error('Este arquivo não parece ser o relatório ABC de venda com loja e data (colunas Quebra e Quebra2).');
    }
    const out = [];
    for (const r of rows) {
      const m = /^(\d+)/.exec((r[0] || '').trim());
      const dm = /^(\d{2})\/(\d{2})\/(\d{4})/.exec((r[1] || '').trim());
      if (!m || !dm) continue;
      out.push({ bcps: +m[1], dt: dm[3] + '-' + dm[2] + '-' + dm[1], sku: stripZeros(r[2]), desc: (r[3] || '').trim(), qtd: num(r[4]) || 0, fat: num(r[5]) || 0 });
    }
    return out;
  }

  // saldo de estoque: Quebra 1 (loja) ; Quebra 2 ; Codigo ; Descrição ; EMB ; NCM ; Estoque ; Est. Mín ; Est. Máx ; Custo ; Venda ; Total Custo ; Total Venda
  function parseEstoque(text) {
    const rows = parseCSV(text);
    const head = rows.shift() || [];
    if (head.length < 13 || !/estoque/i.test(head[6] || '')) {
      throw new Error('Este arquivo não parece ser o saldo de estoque (coluna Estoque na 7ª posição).');
    }
    const out = [];
    for (const r of rows) {
      const m = /(\d+)/.exec((r[0] || '').trim());
      if (!m) continue;
      out.push({ bcps: +m[1], sku: stripZeros(r[2]), desc: (r[3] || '').trim(), est: num(r[6]), venda: num(r[10]), tvenda: num(r[12]) });
    }
    return out;
  }

  // ---------- histórico ----------
  // base = {det:{dt,bcps,sku,qtd,fat}, tot:{dt,bcps,fat,qtd}, nomes}
  // novas vendas substituem o (dia, loja) inteiro, como no pipeline original
  function mergeBase(base, vendasList, keepSku) {
    const novos = new Map(); // "dt|bcps" -> linhas (o arquivo mais recente vence)
    for (const vendas of vendasList) {
      const porChave = new Map();
      for (const r of vendas) {
        const k = r.dt + '|' + r.bcps;
        if (!porChave.has(k)) porChave.set(k, []);
        porChave.get(k).push(r);
      }
      for (const [k, rs] of porChave) novos.set(k, rs);
    }
    const det = { dt: [], bcps: [], sku: [], qtd: [], fat: [] };
    const tot = { dt: [], bcps: [], fat: [], qtd: [] };
    const d0 = base.det;
    for (let i = 0; i < d0.dt.length; i++) {
      if (novos.has(d0.dt[i] + '|' + d0.bcps[i])) continue;
      det.dt.push(d0.dt[i]); det.bcps.push(d0.bcps[i]); det.sku.push(d0.sku[i]); det.qtd.push(d0.qtd[i]); det.fat.push(d0.fat[i]);
    }
    const t0 = base.tot;
    for (let i = 0; i < t0.dt.length; i++) {
      if (novos.has(t0.dt[i] + '|' + t0.bcps[i])) continue;
      tot.dt.push(t0.dt[i]); tot.bcps.push(t0.bcps[i]); tot.fat.push(t0.fat[i]); tot.qtd.push(t0.qtd[i]);
    }
    const nomes = Object.assign({}, base.nomes);
    for (const [k, rs] of novos) {
      const [dt, b] = k.split('|');
      let f = 0, q = 0;
      const agg = new Map();
      for (const r of rs) {
        f += r.fat; q += r.qtd;
        if (!(r.sku in nomes)) nomes[r.sku] = r.desc;
        if (!keepSku(r.sku)) continue;
        const a = agg.get(r.sku) || { qtd: 0, fat: 0 };
        a.qtd += r.qtd; a.fat += r.fat; agg.set(r.sku, a);
      }
      tot.dt.push(dt); tot.bcps.push(+b); tot.fat.push(Math.round(f * 100) / 100); tot.qtd.push(Math.round(q * 1000) / 1000);
      for (const [s, a] of agg) {
        det.dt.push(dt); det.bcps.push(+b); det.sku.push(s);
        det.qtd.push(Math.round(a.qtd * 1000) / 1000); det.fat.push(Math.round(a.fat * 100) / 100);
      }
    }
    return { det, tot, nomes, novas: [...novos.keys()] };
  }

  // ---------- cálculo ----------
  const ddmm = (iso) => iso ? iso.slice(8, 10) + '/' + iso.slice(5, 7) : '';
  const addDays = (iso, n) => { const d = new Date(iso + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
  const diffDays = (a, b) => Math.round((new Date(b + 'T12:00:00Z') - new Date(a + 'T12:00:00Z')) / 86400000);
  const r2 = (x) => Math.round(x * 100) / 100;
  const r4 = (x) => (x == null || isNaN(x)) ? null : Math.round(x * 10000) / 10000;

  function compute(ref, base, estoque, opts) {
    const HOJE = opts.hoje;               // última data com venda (yyyy-mm-dd)
    const frac = opts.frac;               // fração do último dia já vendida
    const DIAS = diffDays(ref.ini_bw, HOJE) + frac;
    const REST = Math.max(0, diffDays(HOJE, ref.fim_bw));

    // lojas
    const loja = new Map(ref.lojas.map((l) => [l.bcps, l]));
    // master BW
    const direct = new Set(ref.agg.map((a) => a.sku));
    const todos = new Map(), porRegra = new Map();
    for (const a of ref.agg) {
      if (a.canal_regra === 'Todos') todos.set(a.sku, a); else porRegra.set(a.sku + '|' + a.canal_regra, a);
    }
    const skuBw = (s) => direct.has(s) ? s : (ref.alias[s] || s);
    const FIELDS = ['desc_bw', 'marca_bw', 'marca', 'cat', 'mec', 'periodo', 'ini', 'fim', 'desc_pct', 'esquenta'];
    const attachCache = new Map();
    const attach = (sku, bcps) => {
      const l = loja.get(bcps);
      const regra = l ? l.regra : null;
      const key = sku + '|' + regra;
      if (attachCache.has(key)) return attachCache.get(key);
      const sb = skuBw(sku);
      const a = todos.get(sb), b = regra ? porRegra.get(sb + '|' + regra) : null;
      let m = null;
      if (a || b) {
        m = { sku_bw: sb };
        for (const f of FIELDS) { const va = a ? a[f] : null; m[f] = (va != null) ? va : (b ? b[f] : null); }
      }
      const res = m ? Object.assign(m, { is_bw: m.marca_bw != null }) : { sku_bw: sb, is_bw: false };
      attachCache.set(key, res);
      return res;
    };
    const active = (m, d) => {
      if (!m.is_bw) return false;
      let on = m.ini != null && m.fim != null && m.ini <= d && m.fim >= d;
      const w = ref.esq[m.marca_bw];
      if (w && m.esquenta === true && d >= w[0] && d <= w[1]) on = true;
      return on;
    };
    const status = (m) => !m.is_bw ? 'Fora BW' : (active(m, HOJE) ? 'Em vigência' : 'Inicia ' + ddmm(m.ini));

    // V: vendas detalhadas (só BW + SKUs do estoque) e totais por loja-dia
    const det = base.det, tot = base.tot;
    const V = [];
    for (let i = 0; i < det.dt.length; i++) {
      const m = attach(det.sku[i], det.bcps[i]);
      V.push({ dt: det.dt[i], bcps: det.bcps[i], sku: det.sku[i], qtd: det.qtd[i], fat: det.fat[i], m });
    }
    const Vb = V.filter((r) => r.m.is_bw);

    // E: estoque
    const E = estoque.map((r) => ({ ...r, m: attach(r.sku, r.bcps) }));

    // G: loja x sku BW
    const G = new Map();
    const gk = (b, s) => b + '|' + s;
    const gget = (b, s) => {
      const k = gk(b, s);
      let g = G.get(k);
      if (!g) { g = { bcps: b, sku: s, qtd: 0, fat: 0, fat_ativo: 0, est: 0, est_val: 0 }; G.set(k, g); }
      return g;
    };
    for (const r of Vb) {
      const g = gget(r.bcps, r.sku);
      g.qtd += r.qtd; g.fat += r.fat; if (active(r.m, r.dt)) g.fat_ativo += r.fat;
    }
    for (const r of E) {
      if (!r.m.is_bw) continue;
      const g = gget(r.bcps, r.sku);
      g.est += isNaN(r.est) ? 0 : r.est; g.est_val += isNaN(r.tvenda) ? 0 : r.tvenda;
    }
    const GL = [...G.values()].map((g) => {
      const m = attach(g.sku, g.bcps), l = loja.get(g.bcps) || {};
      return Object.assign(g, { m, status: status(m), praca: l.praca, canal: l.canal, marca_bw: m.marca_bw || '?' });
    });
    const ATV = GL.filter((g) => g.status === 'Em vigência');

    const giro = (rows) => {
      let q = 0, f = 0, e = 0, ev = 0;
      for (const r of rows) { q += r.qtd; f += r.fat; e += r.est; ev += r.est_val; }
      return { qtd: q, fat: f, est: e, est_val: ev, st: (q + e) ? q / (q + e) : null, cob: q ? e / (q / DIAS) : null };
    };
    const groupBy = (rows, keyFn) => {
      const mp = new Map();
      for (const r of rows) { const k = keyFn(r); if (k == null) continue; if (!mp.has(k)) mp.set(k, []); mp.get(k).push(r); }
      return mp;
    };

    // receita por loja
    const totLoja = new Map(), bwLoja = new Map();
    for (let i = 0; i < tot.dt.length; i++) totLoja.set(tot.bcps[i], (totLoja.get(tot.bcps[i]) || 0) + tot.fat[i]);
    for (const r of Vb) bwLoja.set(r.bcps, (bwLoja.get(r.bcps) || 0) + r.fat);
    const ids = [...new Set([...totLoja.keys(), ...ATV.map((g) => g.bcps)])].sort((a, b) => a - b);
    const atvLoja = groupBy(ATV, (g) => g.bcps);
    const L = [];
    for (const b of ids) {
      const l = loja.get(b) || {};
      const rows = atvLoja.get(b) || [];
      const gi = rows.length ? giro(rows) : { qtd: null, fat: null, est: null, est_val: null, st: null, cob: null };
      const rup = new Set(rows.filter((g) => g.qtd > 0 && g.est <= 0).map((g) => g.sku)).size;
      const sem = new Set(rows.filter((g) => g.qtd === 0 && g.est > 0).map((g) => g.sku)).size;
      const ft = totLoja.get(b) || 0, fb = bwLoja.get(b) || 0;
      if (!(ft > 0 || (gi.est != null && gi.est > 0))) continue;
      L.push({ bcps: b, loja: l.nome, praca: l.praca, canal: l.canal, cluster: l.cluster, fat_total: ft, fat_bw: fb, fat_bw_vig: fb,
        qtd: gi.qtd, est: gi.est, est_val: gi.est_val, skus_ruptura: rup, skus_sem_venda: sem });
    }
    const Lx = L.filter((r) => r.canal !== 'Outros').map((r) => ({
      bcps: String(r.bcps), loja: r.loja, praca: r.praca, canal: r.canal, cluster: r.cluster,
      fat_total: r4(r.fat_total), fat_bw: r4(r.fat_bw), fat_bw_vig: r4(r.fat_bw_vig),
      qtd: Math.trunc(r.qtd || 0), est: Math.trunc(r.est || 0), est_val: r4(r.est_val), skus_ruptura: r.skus_ruptura, skus_sem_venda: r.skus_sem_venda }));

    // praça x canal
    const cmp = (a, b) => a < b ? -1 : a > b ? 1 : 0;
    const PCg = groupBy(L.filter((r) => r.praca != null && r.canal != null), (r) => r.praca + '\u0001' + r.canal);
    const atvPC = groupBy(ATV.filter((g) => g.praca != null && g.canal != null), (g) => g.praca + '\u0001' + g.canal);
    const PCx = [...PCg.keys()].sort(cmp).map((k) => {
      const rs = PCg.get(k), [praca, canal] = k.split('\u0001');
      const gi = atvPC.has(k) ? giro(atvPC.get(k)) : { qtd: 0, est: 0 };
      return { praca, canal, lojas: new Set(rs.map((r) => r.bcps)).size, fat_total: r4(rs.reduce((s, r) => s + r.fat_total, 0)),
        fat_bw_vig: r4(rs.reduce((s, r) => s + r.fat_bw_vig, 0)), qtd: Math.trunc(gi.qtd || 0), est: Math.trunc(gi.est || 0) };
    }).filter((r) => r.canal !== 'Outros');

    // totais por dia x praça x canal
    const DTm = new Map();
    for (let i = 0; i < tot.dt.length; i++) {
      const l = loja.get(tot.bcps[i]); if (!l || l.praca == null || l.canal == null) continue;
      const k = tot.dt[i] + '\u0001' + l.praca + '\u0001' + l.canal;
      const a = DTm.get(k) || { fat_total: 0, qtd_total: 0 };
      a.fat_total += tot.fat[i]; a.qtd_total += tot.qtd[i]; DTm.set(k, a);
    }
    const DTx = [...DTm.keys()].sort(cmp).map((k) => { const [dt, praca, canal] = k.split('\u0001'); const a = DTm.get(k);
      return { dt, praca, canal, fat_total: r4(a.fat_total), qtd_total: r4(a.qtd_total) }; }).filter((r) => r.canal !== 'Outros');

    // diário por canal
    const Dm = new Map();
    for (let i = 0; i < tot.dt.length; i++) {
      const l = loja.get(tot.bcps[i]); if (!l || l.canal == null) continue;
      const k = tot.dt[i] + '\u0001' + l.canal; const a = Dm.get(k) || { fat_total: 0, fat_bw: 0 }; a.fat_total += tot.fat[i]; Dm.set(k, a);
    }
    for (const r of Vb) {
      const l = loja.get(r.bcps); if (!l || l.canal == null) continue;
      const k = r.dt + '\u0001' + l.canal; const a = Dm.get(k) || { fat_total: 0, fat_bw: 0 }; a.fat_bw += r.fat; Dm.set(k, a);
    }
    const Dx = [...Dm.keys()].sort(cmp).map((k) => { const [dt, canal] = k.split('\u0001'); const a = Dm.get(k);
      return { dt, canal, fat_total: r4(a.fat_total), fat_bw: r4(a.fat_bw), fat_bw_vig: r4(a.fat_bw) }; }).filter((r) => r.canal !== 'Outros');

    // BW por dia x praça x canal x tabela, e por SKU
    const DBm = new Map(), DSm = new Map();
    for (const r of Vb) {
      const l = loja.get(r.bcps); if (!l || l.praca == null || l.canal == null) continue;
      const k1 = r.dt + '\u0001' + l.praca + '\u0001' + l.canal + '\u0001' + r.m.marca_bw;
      const a = DBm.get(k1) || { fat: 0, qtd: 0 }; a.fat += r.fat; a.qtd += r.qtd; DBm.set(k1, a);
      const k2 = r.dt + '\u0001' + l.praca + '\u0001' + l.canal + '\u0001' + r.sku;
      const b = DSm.get(k2) || { fat: 0, qtd: 0 }; b.fat += r.fat; b.qtd += r.qtd; DSm.set(k2, b);
    }
    const DBx = [...DBm.keys()].sort(cmp).map((k) => { const [dt, praca, canal, tabela] = k.split('\u0001'); const a = DBm.get(k);
      return { dt, praca, canal, tabela, fat_bw: r4(a.fat), qtd_bw: r4(a.qtd), fat_vig: r4(a.fat), qtd_vig: r4(a.qtd) }; }).filter((r) => r.canal !== 'Outros');
    const DSx = [...DSm.keys()].sort(cmp).map((k) => { const [dt, praca, canal, sku] = k.split('\u0001'); const a = DSm.get(k);
      return { dt, praca, canal, sku, qtd: Math.trunc(a.qtd), fat: r2(a.fat) }; }).filter((r) => r.canal !== 'Outros');

    // SKUs
    const nomes = Object.assign({}, base.nomes);
    for (const r of E) if (!(r.sku in nomes)) nomes[r.sku] = r.desc;
    const Gsku = groupBy(GL, (g) => g.sku);
    const metaSku = new Map();
    for (const a of [...ref.agg].sort((x, y) => cmp(x.canal_regra, y.canal_regra))) {
      if (!metaSku.has(a.sku)) metaSku.set(a.sku, { desc_bw: a.desc_bw, marca_bw: a.marca_bw, cat: a.cat, periodo: a.periodo, desc_pct: a.desc_pct, ini: {}, esquenta: false });
    }
    for (const a of ref.agg) {
      const m = metaSku.get(a.sku);
      if (a.ini && (!m.ini[a.canal_regra] || a.ini < m.ini[a.canal_regra])) m.ini[a.canal_regra] = a.ini;
      if (a.esquenta) m.esquenta = true;
    }
    const allSku = [...new Set([...metaSku.keys(), ...Gsku.keys()])].sort(cmp);
    const Sx = allSku.map((s) => {
      const sb = skuBw(s), m = metaSku.get(sb) || {};
      const rows = Gsku.get(s) || [];
      const gi = rows.length ? giro(rows) : { qtd: 0, fat: 0, est: 0 };
      const iniL = (m.ini || {}).Todos || (m.ini || {}).Loja || null, iniV = (m.ini || {}).Todos || (m.ini || {}).VD || null;
      const vig = (iniV && iniV <= HOJE) || (iniL && iniL <= HOJE) || m.esquenta;
      const mn = [iniL, iniV].filter(Boolean).sort()[0];
      return { sku: s, descricao: nomes[s] != null ? nomes[s] : (m.desc_bw || null), versao_de: s !== sb ? sb : '', tabela: m.marca_bw || null, cat: m.cat || null,
        periodo: m.periodo || null, desc_pct: m.desc_pct != null ? r4(m.desc_pct) : null, status: vig ? 'Em vigência' : 'Inicia ' + ddmm(mn),
        qtd: Math.trunc(gi.qtd || 0), fat: r4(gi.fat || 0), est: Math.trunc(gi.est || 0),
        lojas_c_est: rows.filter((g) => g.est > 0).length, lojas_ruptura: rows.filter((g) => g.qtd > 0 && g.est <= 0).length };
    });

    // tabela x status
    const Mm = groupBy(GL.filter((g) => g.canal !== 'Outros'), (g) => g.marca_bw + '\u0001' + g.status);
    const Mx = [...Mm.keys()].sort(cmp).map((k) => { const [tabela, st] = k.split('\u0001'); const rs = Mm.get(k);
      return { tabela, status: st, qtd: r4(rs.reduce((s, r) => s + r.qtd, 0)), fat: r4(rs.reduce((s, r) => s + r.fat, 0)), est: r4(rs.reduce((s, r) => s + r.est, 0)) }; });

    // fora da tabela
    const excl = new Set([...direct, ...Object.keys(ref.alias)]);
    const FLm = new Map();
    for (const r of E) {
      if (r.m.is_bw || excl.has(r.sku)) continue;
      const k = r.sku + '\u0001' + r.desc; const a = FLm.get(k) || { est: 0, lojas: new Set() };
      a.est += isNaN(r.est) ? 0 : r.est; a.lojas.add(r.bcps); FLm.set(k, a);
    }
    const fv = new Map();
    for (const r of V) { if (r.m.is_bw) continue; const a = fv.get(r.sku) || { qtd: 0, fat: 0 }; a.qtd += r.qtd; a.fat += r.fat; fv.set(r.sku, a); }
    const Fx = [...FLm.keys()].sort(cmp).map((k) => { const [sku, d] = k.split('\u0001'); const a = FLm.get(k); const f = fv.get(sku) || { qtd: 0, fat: 0 };
      return { sku, descricao: d, qtd: r4(f.qtd), fat: r4(f.fat), est: r4(a.est), lojas: a.lojas.size }; }).sort((a, b) => b.fat - a.fat);

    // lojas por dia
    const LxMap = new Map(Lx.map((r) => [r.bcps, r]));
    const LDm = new Map();
    for (let i = 0; i < tot.dt.length; i++) {
      const l = loja.get(tot.bcps[i]); if (l && l.canal === 'Outros') continue;
      const k = tot.bcps[i] + '|' + tot.dt[i]; const a = LDm.get(k) || { fat_total: 0, fat_bw_vig: 0, qtd: 0 }; a.fat_total += tot.fat[i]; LDm.set(k, a);
    }
    for (const r of Vb) {
      const l = loja.get(r.bcps); if (l && l.canal === 'Outros') continue;
      const k = r.bcps + '|' + r.dt; const a = LDm.get(k) || { fat_total: 0, fat_bw_vig: 0, qtd: 0 };
      a.fat_bw_vig += r.fat; if (status(r.m) === 'Em vigência') a.qtd += r.qtd; LDm.set(k, a);
    }
    const LD = [];
    for (const r of Lx) LD.push({ bcps: r.bcps, dt: 'total', loja: r.loja, praca: r.praca, canal: r.canal, fat_total: r.fat_total, fat_bw_vig: r.fat_bw_vig, qtd: r.qtd, est: r.est, est_val: r.est_val, skus_ruptura: r.skus_ruptura });
    for (const k of [...LDm.keys()].sort()) {
      const [b, dt] = k.split('|'); const x = LxMap.get(b); if (!x) continue; const a = LDm.get(k);
      LD.push({ bcps: b, dt, loja: x.loja, praca: x.praca, canal: x.canal, fat_total: r4(a.fat_total), fat_bw_vig: r4(a.fat_bw_vig), qtd: Math.trunc(a.qtd), est: x.est, est_val: x.est_val, skus_ruptura: x.skus_ruptura });
    }

    // estoque por loja x sku
    let ult = ''; for (const d of tot.dt) if (d > ult) ult = d;
    const hj = new Map();
    for (const r of Vb) if (r.dt === ult) hj.set(r.bcps + '|' + r.sku, (hj.get(r.bcps + '|' + r.sku) || 0) + r.qtd);
    const EX = GL.filter((g) => g.canal !== 'Outros' && (g.est > 0 || g.qtd > 0))
      .sort((a, b) => a.bcps - b.bcps || cmp(a.sku, b.sku))
      .map((g) => ({ bcps: String(g.bcps), sku: g.sku, qtd: Math.trunc(g.qtd), fat: r2(g.fat), est: Math.trunc(g.est), qtd_hoje: Math.trunc(hj.get(g.bcps + '|' + g.sku) || 0) }));

    // potencial em estoque por praça
    const PPm = groupBy(GL.filter((g) => g.canal !== 'Outros' && g.praca != null), (g) => g.praca);
    const rv = groupBy(L.filter((r) => r.canal !== 'Outros' && r.praca != null), (r) => r.praca);
    const PP = [...PPm.keys()].sort(cmp).map((p) => {
      const rs = PPm.get(p); let est = 0, pv = 0, pf = 0;
      for (const g of rs) { const pot = g.est_val * (1 - (g.m.desc_pct || 0)); est += g.est; if (g.status === 'Em vigência') pv += pot; else pf += pot; }
      const lr = rv.get(p) || [];
      const ft = lr.length ? lr.reduce((s, r) => s + r.fat_total, 0) : null, fb = lr.length ? lr.reduce((s, r) => s + r.fat_bw_vig, 0) : null;
      return { praca: p, est: Math.trunc(est), pot_vig: r2(pv), pot_fut: r2(pf), fat_total: r4(ft), fat_bw_vig: r4(fb), pot: r4(r2(pv) + r2(pf)) };
    });

    const meta = [{ hoje: HOJE, ultima: ddmm(HOJE), dias: Math.round(DIAS * 10) / 10, rest: REST, frac, hora: opts.hora || '', estoque: opts.estoqueData ? ddmm(opts.estoqueData) : '',
      parcial: frac < 1, gerado: new Date().toISOString() }];

    return { lojas: Lx, praca_canal: PCx, diario: Dx, skus: Sx, marcas: Mx, fora_tabela: Fx, dia_total: DTx, dia_bw: DBx, dia_sku: DSx,
      estoque: EX, lojas_dia: LD, praca_pot: PP, meta };
  }

  const api = { parseCSV, parseVendas, parseEstoque, mergeBase, compute, ddmm, addDays, diffDays };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.BWEngine = api;
})(this);
