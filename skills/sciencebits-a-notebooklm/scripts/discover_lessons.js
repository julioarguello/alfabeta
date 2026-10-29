// Run on a Science Bits UNIT page (/intranet/<lang>/myclasses/unit?code=...).
// Returns {sem, rest, lessons:[{n, lessonId}], listText, unitTitle} for orchestrator.js.
// Lessons open via window.open, so we intercept it (no window is actually opened).
(async () => {
  const hex2s = h => h.match(/../g).map(b => String.fromCharCode(parseInt(b, 16))).join('');
  const opened = [];
  const orig = window.open;
  // Science Bits alerts «Tu navegador tiene bloqueadas las ventanas emergentes.» when window.open
  // returns nothing, and the alert freezes the tab (measured 2026-10-29). With a window it only calls
  // newwindow.focus() (read in the page the same day), so the stub hands back a stand-in window.
  window.open = (u) => { opened.push(u); return { closed: false, focus() {}, close() {}, location: {} }; };
  const btns = [...document.querySelectorAll('[onclick^="verleccion1"]')];
  for (const b of btns) { b.click(); await new Promise(r => setTimeout(r, 600)); }
  window.open = orig;
  let box = btns[0]; while (box && !(box.innerText || '').match(/\n\s*2\s*\n/)) box = box.parentElement;
  const lines = (box ? box.innerText : '').split('\n').map(s => s.trim()).filter(Boolean);
  let sem = null, rest = null;
  const lessons = opened.map((u, i) => {
    const url = new URL(u, location.origin);
    sem = url.searchParams.get('sem');
    const dec = hex2s(url.searchParams.get('code'));        // e.g. "l1h1234_es&repertorio=111&unidad=222"
    const amp = dec.indexOf('&');
    rest = dec.slice(amp);                                 // "&repertorio=...&unidad=..."
    const lessonId = dec.slice(0, amp).replace(/_(es|eu|en)$/, '');
    return {n: i + 1, lessonId};
  });
  const unitTitle = (document.querySelector('.unidad-titulo, .titulo-unidad, h1, h2')?.innerText || '').trim();
  return {unitTitle, sem, rest, count: lessons.length, lessons, listText: lines.slice(0, 80).join(' | ')};
})()
