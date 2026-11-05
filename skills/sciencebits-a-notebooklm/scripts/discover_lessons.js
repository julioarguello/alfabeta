// Run on the Science Bits classes page (/intranet/<lang>/myclasses/index), with the unit's class open, after setting
//   window.__UNIT = {name: '<the unit's title on this page>', langs: ['es', 'en', ...]}
// and do not navigate afterwards: what it finds lives in this tab. It reads the unit's page in each language in a
// hidden iframe, because what the teacher shows differs by language and by lesson.
// window.__SB: {queue: [{lang, id, sem, code, title}]}, the lessons to capture, for orchestrator.js.
// Returns what it found per language, never `sem` or `code`: Claude in Chrome blanks query-string data in a result
// («[BLOCKED…]», measured 2026-11-05), so they only work from inside the page. Nothing here opens a lesson or an
// assessment; a hidden lesson or an assessment is not even clicked.
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const text = e => (e.textContent || '').replace(/\s+/g, ' ').trim();
  // The last phase of a unit and the title of its assessment, in each language render.py knows.
  const ASSESSMENT = /\b(Evaluamos|Evaluaci[oó]n|Ebaluatu|Ebaluazioa|Evaluate|Evaluation|Assessment)\b/i;
  const LOAD_MS = 20000;
  const SETTLE_MS = 1500;
  const CLICK_MS = 600;

  delete window.__SB;   // a failed discovery must not leave another unit's queue for orchestrator.js
  const {name, langs} = window.__UNIT;
  const links = [...document.querySelectorAll('a.btn-acceder:not(.desactivado)')]
    .filter(a => text(a.closest('.box-center-unidad') || a).includes(name));
  if (links.length !== 1) return {error: links.length ? 'ambiguous_unit' : 'unit_not_shown_on_this_page', name};
  const unitUrl = links[0].href;

  const frame = document.createElement('iframe');
  frame.style.cssText = 'position:fixed;left:-3000px;width:1280px;height:800px';
  document.body.appendChild(frame);

  const readLanguage = async (lang) => {
    const loaded = new Promise(r => { frame.onload = () => r(true); });
    frame.src = unitUrl.replace(/\/intranet\/[a-z]+\//, '/intranet/' + lang + '/');
    if (!await Promise.race([loaded, sleep(LOAD_MS).then(() => false)])) return {error: 'no_load'};
    await sleep(SETTLE_MS);
    const win = frame.contentWindow, doc = frame.contentDocument;
    if (win.location.href.includes('/login')) return {error: 'SESSION_EXPIRED'};
    const found = {lessons: [], hidden: [], assessments: [], unread: []};
    const opened = [];
    const original = win.open;
    // Science Bits alerts «Tu navegador tiene bloqueadas las ventanas emergentes.» when window.open returns nothing,
    // and the alert freezes the tab (measured 2026-10-29). With a window it only calls newwindow.focus().
    win.open = (u) => { opened.push(u); return {closed: false, focus() {}, close() {}, location: {}}; };
    for (const row of doc.querySelectorAll('.box-center-unidad.margin-vertical-0')) {
      const title = text(row);
      if (row.classList.contains('leccion-bloqueada')) { found.hidden.push(title); continue; }
      if (ASSESSMENT.test(title)) { found.assessments.push(title); continue; }
      const button = row.parentElement.querySelector('[onclick^="verleccion1"]');
      if (!button) { found.unread.push(title); continue; }
      const before = opened.length;
      button.click();
      await sleep(CLICK_MS);
      if (opened.length === before) { found.unread.push(title); continue; }
      const url = new URL(opened[before], location.origin);
      found.lessons.push({title, sem: url.searchParams.get('sem'), code: url.searchParams.get('code')});
    }
    win.open = original;
    return found;
  };

  const report = {};
  const queue = [];
  for (const lang of langs) {
    const found = await readLanguage(lang);
    if (found.error) {
      frame.remove();
      return {error: found.error, lang};
    }
    found.lessons.forEach((lesson, i) => queue.push({lang, id: 'L' + (i + 1), ...lesson}));
    report[lang] = {
      lessons: found.lessons.map(lesson => lesson.title),
      hidden: found.hidden,
      assessments: found.assessments,
      unread: found.unread,
    };
  }
  frame.remove();
  window.__SB = {queue};
  return {name, queued: queue.length, langs: report};
})()
