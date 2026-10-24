// Science Bits capture orchestrator. Run in a learning-bits.com tab (logged in) whose viewport is 1280x800.
// Before running, set:
//   window.__SB = {sem:'<sem>', rest:'&repertorio=..&unidad=..', queue:[{lang:'es', id:'L1', lessonId:'l1h1234'}, ...]}
//   (sem, rest and lessonId come from discover_lessons.js)
// Each lesson opens in a same-origin iframe; the job inside captures every screen (and every
// button state) with html2canvas, stores text + cleaned HTML, zips it and downloads sb_<lang>_<id>.zip.
// Poll window.__orch: {done, results:[{tag,n,size,err}], current, stopped}. Keep each poll call short (<40 s).
(() => {
const jobFn = async () => {
  const cfg = window.__CFG || {tag: 'x'};
  const job = window.__job = {done: false, err: null, n: 0, log: []};
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const ld = u => new Promise((res, rej) => {const s = document.createElement('script'); s.src = u; s.onload = res; s.onerror = () => rej('load ' + u); document.head.appendChild(s);});
  const cleanHtml = (p) => { const c = p.cloneNode(true); c.querySelectorAll('svg,script,style,canvas,video,audio,button,.hovericon').forEach(e => e.remove()); c.querySelectorAll('*').forEach(e => { [...e.attributes].forEach(a => { if (!['class','id','src','alt'].includes(a.name)) e.removeAttribute(a.name); }); }); return c.innerHTML; };
  try {
    if (typeof html2canvas === 'undefined') await ld('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js');
    if (typeof JSZip === 'undefined') await ld('https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js');
    const zip = new JSZip(); const meta = {tag: cfg.tag, title: document.title, items: []};
    const vis = e => e && e.offsetParent;
    const btn = cls => [...document.querySelectorAll('.' + cls)].find(e => vis(e) && !e.classList.contains('disabled') && !e.classList.contains('tempDisabled'));
    const cur = () => document.querySelector('page.showing');
    const settle = async () => { for (let i = 0; i < 30; i++) { const p = cur(); if (p && p.classList.contains('loaded') && [...p.querySelectorAll('img')].every(im => im.complete)) break; await sleep(300);} await sleep(1000); };
    const go = async (cls, tries = 4) => { const id = cur()?.id; for (let t = 0; t < tries; t++) { const b = btn(cls); if (!b) { await sleep(800); continue; } b.click(); for (let i = 0; i < 20; i++) { await sleep(300); if (cur() && cur().id !== id) { await settle(); return true; } } } return false; };
    for (let i = 0; i < 90 && !cur(); i++) { const enter = document.getElementById('enterBut'); if (enter && vis(enter)) enter.click(); await sleep(1000); }
    if (!cur()) throw new Error('no page after enter');
    await settle();
    for (let i = 0; i < 80; i++) { if (!btn('prevBut')) break; if (!(await go('prevBut', 1))) break; if (!cur()) { for (let k = 0; k < 20 && !cur(); k++) { document.getElementById('enterBut')?.click(); await sleep(1000); } break; } }
    meta.menu = [...document.querySelectorAll('#menu .section')].map(s => s.innerText.replace(/\s+/g, ' ').trim());
    const snap = async (p, label) => {const c = await html2canvas(document.querySelector('#root'), {useCORS: true, scale: 1.5, logging: false, backgroundColor: '#ffffff'}); const blob = await new Promise(r => c.toBlob(r, 'image/jpeg', 0.82)); job.n++; const name = String(job.n).padStart(3, '0') + '.jpg'; zip.file(name, blob);
      meta.items.push({file: name, page: p.id, label, text: p.innerText.trim(), html: cleanHtml(p)});};
    const seen = new Set();
    for (let guard = 0; guard < 120; guard++) {
      const p = cur(); if (!p || seen.has(p.id)) break; seen.add(p.id);
      await snap(p, 'base');
      const bots = [...p.querySelectorAll('boliche.akt_tx_boton')].filter(vis);
      for (const b of bots) { b.click(); await sleep(1300); await snap(p, 'boton: ' + b.innerText.trim().slice(0, 80)); }
      job.log.push(p.id + ' (' + (1 + bots.length) + ')');
      if (!(await go('nextBut'))) break;
    }
    zip.file('meta.json', JSON.stringify(meta));
    const out = await zip.generateAsync({type: 'blob'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(out); a.download = 'sb_' + cfg.tag + '.zip'; document.body.appendChild(a); a.click(); job.size = out.size;
  } catch (e) { job.err = String(e); }
  job.done = true;
};
const SB = window.__SB;
window.__orch = {done: false, results: [], current: null, stopped: null};
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const runOne = async (q) => {
    const tag = q.lang + '_' + q.id;
    window.__orch.current = tag;
    document.getElementById('__fr')?.remove();
    const f = document.createElement('iframe'); f.id = '__fr';
    f.style.cssText = 'position:fixed;left:0;top:0;width:1280px;height:800px;z-index:999999;border:0;background:#fff';
    const s2h = s => [...s].map(c => c.charCodeAt(0).toString(16).padStart(2, '0')).join('');
    const code = q.code ? q.code + (SB.tail || '') : s2h(q.lessonId + '_' + q.lang + SB.rest);
    f.src = '/intranet/' + q.lang + '/mylesson/index?sem=' + SB.sem + '&code=' + code;
    document.body.appendChild(f);
    for (let i = 0; i < 60; i++) { await sleep(500); try { const h = f.contentWindow.location.href; if (h.includes('/login')) return {tag, err: 'SESSION_EXPIRED'}; if (/not available|no está disponible|ez dago eskuragarri/i.test(f.contentDocument.body?.innerText || '')) return {tag, err: 'NOT_AVAILABLE'}; if (h.includes('refreshed=true') && f.contentDocument.readyState == 'complete' && f.contentDocument.getElementById('root')) break; } catch (e) {} }
    await sleep(3000);
    f.contentWindow.__CFG = {tag}; f.contentWindow.eval('(' + jobFn.toString() + ')()');
    let j; for (let i = 0; i < 1200; i++) { await sleep(1000); try { if (f.contentWindow.location.href.includes('/login')) return {tag, err: 'SESSION_EXPIRED'}; } catch (e) {} j = f.contentWindow.__job; if (j && j.done) break; }
    return {tag, n: j?.n, size: j?.size, err: j?.err, pages: j?.log?.length};
  };
  const skipLang = new Set();
  for (const q of SB.queue) {
    if (skipLang.has(q.lang)) { window.__orch.results.push({tag: q.lang + '_' + q.id, err: 'NOT_AVAILABLE'}); continue; }
    let r = await runOne(q);
    if (r.err === 'NOT_AVAILABLE') { skipLang.add(q.lang); window.__orch.results.push(r); continue; }
    if (r.err === 'SESSION_EXPIRED') { window.__orch.stopped = 'SESSION_EXPIRED at ' + r.tag; window.__orch.results.push(r); break; }
    if (!r.n) r = await runOne(q);   // one retry
    window.__orch.results.push(r);
    await sleep(2000);
  }
  document.getElementById('__fr')?.remove();
  window.__orch.done = true;
})();
return 'orchestrator started: ' + SB.queue.length;
})()
