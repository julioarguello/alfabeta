// The extractor over the synthetic pages (spec 001 T032, T033; research R11).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { JSDOM, ResourceLoader } from "jsdom";

const PAGES = new URL("../fixtures/classroom/pages/", import.meta.url);
const SOURCE = fs.readFileSync(new URL("../../skills/classroom-sync/scripts/extract.js", import.meta.url), "utf8");
const MARKER = "MARCADOR-QUE-NO-DEBE-SALIR";

function page(name) {
  const dom = new JSDOM(fs.readFileSync(new URL(`${name}.html`, PAGES), "utf8"), { runScripts: "outside-only" });
  dom.window.eval(SOURCE);
  return dom;
}

const extract = page("home").window.alfabetaExtract;

// A fake browser: each allowed path serves a synthetic page; every visit and event is recorded.
function fakeBrowser({ plant = false, override = {} } = {}) {
  let clock = Date.UTC(2026, 9, 27, 15, 0, 0);
  const visits = [];
  const events = [];
  const route = (path) => {
    if (override[path]) return override[path];
    if (/^\/u\/\d+\/w\/[^/]+\/t\/all$/.test(path)) return "classwork";
    if (/\/a\/[^/]+\/details$/.test(path)) return "assignment-detail";
    if (/\/m\/[^/]+\/details$/.test(path)) return "material-detail";
    if (/\/mc\/[^/]+\/details$/.test(path)) return "question-detail";
    if (/^\/u\/\d+\/c\/[^/]+$/.test(path)) return "stream";
    throw new Error(`not an allowed page: ${path}`);
  };
  const load = async (path) => {
    visits.push({ path, at: clock });
    const dom = page(route(path));
    const doc = dom.window.document;
    for (const kind of ["click", "submit"]) doc.addEventListener(kind, (e) => events.push(kind + ":" + e.target.tagName), true);
    dom.window.HTMLFormElement.prototype.submit = () => events.push("form.submit()");
    if (plant) plantPrivate(doc);
    return { doc, path };
  };
  return {
    load,
    visits,
    events,
    now: () => new Date(clock),
    sleep: async (ms) => { clock += ms; },
    random: () => 0.5,
  };
}

// Class comments, private comments and the post's author: none may reach the capture.
function plantPrivate(doc) {
  for (const heading of doc.querySelectorAll("h2")) {
    if (/Comentarios (de la clase|privados)/.test(heading.textContent)) {
      const comment = doc.createElement("div");
      comment.textContent = `${MARKER} comentario`;
      heading.parentElement.parentElement.appendChild(comment);
    }
  }
  const author = doc.querySelector(".rec5Nb .YVvGBb");
  if (author) author.textContent = `${MARKER} autor`;
  // On the stream, each post's header names its author and its class comments sit below it. The
  // marker goes in a node of its own, so a notice still reads «Tarea: …».
  for (const header of doc.querySelectorAll("[data-stream-item-id] .QUEiXc")) {
    const name = doc.createElement("span");
    name.textContent = `${MARKER} autor del anuncio`;
    header.appendChild(name);
  }
  for (const comments of doc.querySelectorAll("[data-stream-item-id] .s2g3Xd")) {
    const comment = doc.createElement("div");
    comment.textContent = `${MARKER} comentario de clase en el tablón`;
    comments.appendChild(comment);
  }
}

async function capture(options) {
  const browser = fakeBrowser(options);
  const result = await extract.captureClass({
    run: "r1", classId: "synth-1", title: "Clase inventada", account: 5, ...browser,
  });
  // Objects built inside jsdom's realm: compare them as JSON, as the capture is written.
  return { result: JSON.parse(JSON.stringify(result)), browser };
}

test("the class list comes from the home page", () => {
  const home = page("home");
  const result = JSON.parse(
    JSON.stringify(extract.captureClasses({ run: "r1", doc: home.window.document, path: "/u/5/h", now: () => new Date() })),
  );
  assert.equal(result.type, "classes");
  assert.equal(result.account_index, 5);
  assert.ok(result.classes.length >= 10, `${result.classes.length} classes`);
  for (const c of result.classes) {
    assert.deepEqual(Object.keys(c).sort(), ["id", "title", "visibility"]);
    assert.match(c.id, /^synth-\d+$/);
    assert.ok(c.title.length > 0);
  }
  assert.equal(new Set(result.classes.map((c) => c.id)).size, result.classes.length);
});

test("a class capture has the keys of the contract and reads every page kind", async () => {
  const { result } = await capture();
  assert.equal(result.type, "class");
  assert.deepEqual(
    Object.keys(result).sort(),
    ["captured_at", "class", "complete", "items", "run", "stream", "topics", "type", "version"],
  );
  assert.equal(result.complete, true);
  assert.deepEqual(result.topics.map((t) => t.order), result.topics.map((_, i) => i + 1));
  assert.ok(result.items.length >= 10);
  assert.deepEqual(new Set(result.items.map((i) => i.type)), new Set(["assignment", "material", "question"]));
  for (const item of result.items) {
    assert.match(item.listing_date_text, /^(Fecha de entrega|Publicado|Sin fecha de entrega|Última modificación)|^$/);
    assert.ok(item.detail.posted_text, "every detail has its posting date");
    assert.ok(result.topics.some((t) => t.id === item.topic), "every item's topic is listed");
  }
  const assignment = result.items.find((i) => i.type === "assignment");
  assert.equal(assignment.detail.status_text, "Calificado");
  assert.match(assignment.detail.modified_text, /^Última modificación: /);
  assert.match(assignment.detail.points, /^\d+ puntos$/);
  assert.match(assignment.detail.due_text, /^Fecha de entrega: /);
  const question = result.items.find((i) => i.type === "question");
  assert.equal(question.detail.status_text, "Sin entregar");
  const material = result.items.find((i) => i.type === "material");
  assert.deepEqual(material.detail.attachments.map((a) => a.kind), ["file"]);
  assert.match(material.detail.attachments[0].id, /^synth-\d+$/);
});

test("an item outside every topic goes to «Sin tema» as topic null", async () => {
  const { result } = await capture();
  const noTopic = result.items.filter((i) => i.topic === null);
  assert.ok(noTopic.length >= 1);
  assert.deepEqual(result.topics.at(-1), { id: null, title: "Sin tema", order: result.topics.length });
});

test("item ids come from their position in the detail URL", async () => {
  const { result, browser } = await capture();
  const details = browser.visits.filter((v) => v.path.endsWith("/details"));
  assert.deepEqual(result.items.map((i) => i.id), details.map((v) => v.path.split("/")[6]));
  // The URL id is the row's numeric id in base64 (research R3, S3).
  for (const visit of details) {
    assert.match(Buffer.from(visit.path.split("/")[6], "base64").toString(), /^\d{10}$/);
  }
});

test("comments and authors never reach the capture", async () => {
  const { result } = await capture({ plant: true });
  assert.ok(!JSON.stringify(result).includes(MARKER));
});

test("a challenge or another interface stops the run", async () => {
  const challenged = await capture({ override: { "/u/5/w/synth-1/t/all": "challenge" } });
  assert.deepEqual(
    { type: challenged.result.type, reason: challenged.result.reason, class: challenged.result.class },
    { type: "stop", reason: "challenge", class: "synth-1" },
  );
  const other = await capture({ override: { "/u/5/w/synth-1/t/all": "classwork-other-language" } });
  assert.equal(other.result.reason, "unexpected_ui");
  const home = page("challenge");
  assert.equal(extract.captureClasses({ run: "r1", doc: home.window.document, path: "/u/5/h", now: () => new Date() }).reason, "challenge");
});

test("read only: no click, no submit, only allowed pages, at least 2 s apart", async () => {
  const { browser } = await capture();
  assert.deepEqual(browser.events, []);
  for (const visit of browser.visits) {
    assert.doesNotMatch(visit.path, /\/sp\/|forms|quiz|\/submissions/);
  }
  for (let i = 1; i < browser.visits.length; i++) {
    assert.ok(browser.visits[i].at - browser.visits[i - 1].at >= extract.MIN_WAIT_MS, `visit ${i} came too soon`);
  }
});

test("the file name carries the run and the class", () => {
  const name = extract.fileName({ type: "class", run: "r1", class: { id: "synth-1" }, captured_at: "2026-10-27T15:22:00Z" });
  assert.equal(name, "alfabeta-capture-r1-synth-1-20261027-152200.json");
});

// What the first real run found (2026-10-27): an expired session, and a page that does not load.
async function captureWith(failOn, error) {
  const browser = fakeBrowser();
  const load = async (path) => {
    if (failOn.test(path)) throw error();
    return browser.load(path);
  };
  const result = await extract.captureClass({ run: "r1", classId: "synth-1", account: 5, ...browser, load });
  return JSON.parse(JSON.stringify(result));
}

test("an expired session stops the class with session_expired", async () => {
  const win = page("home").window;
  const result = await captureWith(/\/m\/[^/]+\/details$/, () => new win.alfabetaExtract.SessionExpired());
  assert.deepEqual({ type: result.type, reason: result.reason, class: result.class }, { type: "stop", reason: "session_expired", class: "synth-1" });
});

test("a page that does not load leaves the capture incomplete, not aborted", async () => {
  const full = await capture();
  const result = await captureWith(/\/m\/[^/]+\/details$/, () => new Error("timeout"));
  assert.equal(result.type, "class");
  assert.equal(result.complete, false);
  assert.ok(result.items.length > 0 && result.items.length < full.result.items.length);
  assert.ok(result.items.every((i) => i.type !== "material"));
});

test("readiness per page kind on the synthetic pages", () => {
  const ready = (name, path) => extract.pageReady(path, page(name).window.document);
  assert.equal(ready("classwork", "/u/5/w/synth-1/t/all"), true);
  assert.equal(ready("assignment-detail", "/u/5/c/synth-1/a/x/details"), true);
  assert.equal(ready("material-detail", "/u/5/c/synth-1/m/x/details"), true);
  assert.equal(ready("stream", "/u/5/c/synth-1"), true);
  assert.equal(ready("challenge", "/u/5/w/synth-1/t/all"), false);
});

test("«Ayer» is a posting date", () => {
  const dom = page("assignment-detail");
  const doc = dom.window.document;
  const posted = [...doc.querySelectorAll("div")].find((d) => /^\d{1,2} \w+ \(Última modificación/.test(d.textContent.trim()) && d.children.length === 0);
  posted.textContent = "Ayer";
  assert.equal(dom.window.alfabetaExtract.readDetail(doc).posted_text, "Ayer");
});

test("an attachment is named by its file, without the label's prefix", () => {
  const doc = new JSDOM(
    '<a href="https://drive.google.com/file/d/synth-1/view" aria-label="Archivo adjunto: Microsoft Word: ficha inventada.docx">x</a>' +
    '<a href="https://www.youtube.com/watch?v=synth-2" aria-label="Archivo adjunto: vídeo de YouTube: Vídeo inventado">y</a>',
  ).window.document;
  const [file, video] = [...doc.querySelectorAll("a")].map((a) => extract.attachmentOf(a));
  assert.equal(file.name, "ficha inventada.docx");
  assert.equal(video.name, "Vídeo inventado");
});

test("an attachment labelled without its type is still named by its file", () => {
  const doc = new JSDOM(
    '<a href="https://drive.google.com/file/d/synth-3/view" aria-label="Archivo adjunto: imagen inventada.jpg">z</a>',
  ).window.document;
  assert.equal(extract.attachmentOf(doc.querySelector("a")).name, "imagen inventada.jpg");
});

test("the loader loads nothing while the tab is hidden, and goes on when it is shown", async () => {
  const dom = new JSDOM("<body></body>", { url: "https://classroom.google.com/u/5/h", runScripts: "outside-only" });
  dom.window.eval(SOURCE);
  const doc = dom.window.document;
  let state = "hidden";
  Object.defineProperty(doc, "visibilityState", { get: () => state });
  try {
    const loading = dom.window.alfabetaExtract.iframeLoader(dom.window, { timeoutMs: 200, attempts: 1 })("/u/5/w/synth-1/t/all");
    const outcome = loading.then(() => "loaded", (err) => err.message);
    await new Promise((r) => setTimeout(r, 400));
    assert.equal(doc.querySelectorAll("iframe").length, 0); // hidden for longer than the timeout: still waiting
    state = "visible";
    doc.dispatchEvent(new dom.window.Event("visibilitychange"));
    await new Promise((r) => setTimeout(r, 50));
    assert.equal(doc.querySelectorAll("iframe").length, 1);
    assert.equal(await outcome, "timeout"); // a blank frame never gets ready: the timeout runs once shown
  } finally {
    dom.window.close(); // its timers would otherwise keep the run alive
  }
});

test("a description keeps its line breaks and joins its inline marks", () => {
  const doc = new JSDOM(
    '<div role="main"><div class="nGi02b"><span>Ejercicios 1 y 2.<br>Mañana <b>los</b> corrijo.<br><br>Saludos</span></div></div>',
  ).window.document;
  assert.equal(extract.readDetail(doc).description, "Ejercicios 1 y 2.\nMañana los corrijo.\n\nSaludos");
});

// A class whose «Trabajo de clase» is empty shows only «Aún no hay tareas…» (measured 2026-10-28):
// its page is ready with no rows, and the capture is a class with no items, read twice to be sure.
function emptyClasswork() {
  const dom = page("classwork");
  const doc = dom.window.document;
  for (const node of doc.querySelectorAll("li[data-stream-item-type], [data-topic-id][role=region]")) node.remove();
  const note = doc.createElement("div");
  note.textContent = "Aún no hay tareas. ¡Qué suerte tienes!";
  doc.body.appendChild(note);
  return doc;
}

test("an empty «Trabajo de clase» is ready and gives a class with no items", async () => {
  assert.equal(extract.pageReady("/u/5/w/synth-1/t/all", emptyClasswork()), true);
  const browser = fakeBrowser();
  const load = async (path) => (/\/t\/all$/.test(path) ? (browser.visits.push({ path, at: 0 }), { doc: emptyClasswork(), path }) : browser.load(path));
  const result = JSON.parse(JSON.stringify(await extract.captureClass({ run: "r1", classId: "synth-1", account: 5, ...browser, load })));
  assert.equal(result.type, "class");
  assert.equal(result.complete, true);
  assert.deepEqual([result.items, result.topics], [[], []]);
  assert.equal(browser.visits.filter((v) => v.path.endsWith("/t/all")).length, 2);
});

test("a classwork page with neither rows nor the empty notice is not ready", () => {
  const doc = emptyClasswork();
  for (const div of doc.querySelectorAll("div")) if (div.textContent.startsWith("Aún no hay tareas")) div.remove();
  assert.equal(extract.pageReady("/u/5/w/synth-1/t/all", doc), false);
});

// The stream as the real page builds it (measured 2026-10-28): the body's lines are split by <br>,
// every post hides a teacher-only notice, longer than any of those lines, in a tooltip, and the
// label «Fecha de creación: » and its date are two text nodes, which a saved page joins into one.
test("each announcement is read whole, line by line, with its creation date", () => {
  const doc = page("stream-announcements").window.document;
  const expected = [
    {
      id: "9100000001",
      created_text: "Fecha de creación: 22 sept",
      text: "El examen del martes entra:\nMagnitudes y unidades.\nNotación científica.",
      attachments: [],
    },
    { id: "9100000002", created_text: "Fecha de creación: 27 oct", text: "Mañana, examen.", attachments: [] },
  ];
  assert.deepEqual(JSON.parse(JSON.stringify(extract.readStream(doc))), expected);
  for (const label of doc.querySelectorAll(".JZk9qf > .jzdBjc")) label.firstChild.splitText("Fecha de creación: ".length);
  assert.deepEqual(JSON.parse(JSON.stringify(extract.readStream(doc))), expected);
});

// T046: a post's attachments are read; a link a classmate leaves in its class comments is not (FR-009).
test("an announcement's attachment is read, and a link in its class comments is not", () => {
  const doc = page("stream-announcements").window.document;
  const body = doc.querySelector(".pco8Kc");
  const post = body.closest("[data-stream-item-id]");
  const file = doc.createElement("a");
  file.setAttribute("href", "https://drive.google.com/file/d/synth-90/view");
  file.setAttribute("aria-label", "Archivo adjunto: PDF: normas inventadas.pdf");
  body.parentElement.appendChild(file);
  const comment = doc.createElement("a");
  comment.setAttribute("href", "https://example.org/enlace-inventado-de-un-comentario");
  comment.textContent = `${MARKER} enlace de un comentario`;
  post.querySelector(".s2g3Xd").appendChild(comment);
  const stream = JSON.parse(JSON.stringify(extract.readStream(doc)));
  assert.deepEqual(stream[0].attachments, [{ id: "synth-90", kind: "file", name: "normas inventadas.pdf" }]);
  assert.ok(!JSON.stringify(stream).includes(MARKER));
});

test("a short announcement is not taken for its author, nor a comment for an announcement", async () => {
  const { result } = await capture({ plant: true, override: { "/u/5/c/synth-1": "stream-announcements" } });
  assert.ok(!JSON.stringify(result).includes(MARKER));
  assert.deepEqual(result.stream.map((p) => p.text), [
    "El examen del martes entra:\nMagnitudes y unidades.\nNotación científica.",
    "Mañana, examen.",
  ]);
});

test("an announcement whose body or comment starts like a notice is still read", () => {
  const doc = page("stream-announcements").window.document;
  const [first, second] = doc.querySelectorAll(".pco8Kc > span");
  second.textContent = "Tarea: traed el cuaderno.";
  const comment = doc.createElement("div");
  comment.textContent = "Pregunta: ¿entra el tema 2?";
  first.closest("[data-stream-item-id]").querySelector(".s2g3Xd").appendChild(comment);
  const stream = JSON.parse(JSON.stringify(extract.readStream(doc)));
  assert.deepEqual(stream.map((p) => [p.id, p.text.split("\n")[0]]), [
    ["9100000001", "El examen del martes entra:"],
    ["9100000002", "Tarea: traed el cuaderno."],
  ]);
});

test("an empty stream is ready", () => {
  const doc = page("stream").window.document;
  for (const node of doc.querySelectorAll("[data-stream-item-id]")) node.remove();
  assert.equal(extract.pageReady("/u/5/c/synth-1", doc), false);
  const note = doc.createElement("div");
  note.textContent = "Aquí se mostrarán novedades de esta clase";
  doc.body.appendChild(note);
  assert.equal(extract.pageReady("/u/5/c/synth-1", doc), true);
  assert.deepEqual(JSON.parse(JSON.stringify(extract.readStream(doc))), []);
});

// The loader over real frames: jsdom serves each path a synthetic page, so the test can change it
// after it is ready, as Classroom does while it paints (#264).
const DETAIL = "/u/5/c/synth-1/m/synth-2/details";
const FAST = { timeoutMs: 3000, attempts: 1, settleMs: 200, settleCapMs: 3000, pollMs: 20 };

// The material page with its one attachment taken out; `late` puts it back where it was.
function lateAttachment() {
  const dom = page("material-detail");
  const X = dom.window.alfabetaExtract;
  const anchor = [...dom.window.document.querySelectorAll("a[href]")].find((a) => X.attachmentOf(a) && X.readDetail(dom.window.document).attachments.some((x) => x.id === X.attachmentOf(a).id));
  anchor.parentElement.setAttribute("data-late-slot", "");
  const late = anchor.outerHTML;
  anchor.remove();
  return { html: dom.serialize(), late };
}

function framed(html, path = DETAIL) {
  // Only the page asked for: the synthetic page holds frames of its own, which must not load it again.
  class Serve extends ResourceLoader {
    fetch(url) { return Promise.resolve(Buffer.from(new URL(url).pathname === path ? html : "")); }
  }
  const dom = new JSDOM("<body></body>", { url: "https://classroom.google.com/u/5/h", runScripts: "outside-only", resources: new Serve() });
  dom.window.eval(SOURCE);
  return dom;
}

// The frame's document once the extractor would call it ready.
async function whenReady(dom) {
  const X = dom.window.alfabetaExtract;
  for (;;) {
    const frame = dom.window.document.querySelector("iframe");
    const doc = frame && frame.contentDocument;
    if (doc && doc.location.href !== "about:blank" && doc.body && X.pageReady(DETAIL, doc)) return doc;
    await new Promise((r) => setTimeout(r, 2));
  }
}

const pause = (ms) => new Promise((r) => setTimeout(r, ms));

// The description block the extractor reads (the synthetic material has none), painted with `text`.
function paintDescription(doc, text) {
  let block = doc.querySelector(".nGi02b");
  if (!block) {
    block = doc.createElement("div");
    block.className = "nGi02b";
    doc.querySelector("[data-late-slot]").before(block); // inside the item, as Classroom puts it
  }
  block.textContent = text;
}

test("a page that paints at once is taken within a poll of settleMs after it is ready, as before", { timeout: 5000 }, async () => {
  const dom = framed(page("material-detail").serialize());
  try {
    const loading = dom.window.alfabetaExtract.iframeLoader(dom.window, FAST)(DETAIL);
    await whenReady(dom);
    const readyAt = Date.now();
    const { doc } = await loading;
    const took = Date.now() - readyAt;
    assert.ok(took >= FAST.settleMs - FAST.pollMs && took < FAST.settleMs + 300, `took ${took} ms`);
    assert.equal(dom.window.alfabetaExtract.readDetail(doc).attachments.length, 1);
  } finally {
    dom.window.close();
  }
});

test("a page still painting after it is ready is read once it holds still: the late attachment is in", { timeout: 5000 }, async () => {
  const { html, late } = lateAttachment();
  const dom = framed(html);
  try {
    const loading = dom.window.alfabetaExtract.iframeLoader(dom.window, FAST)(DETAIL);
    const doc = await whenReady(dom);
    // Three paints, each sooner than settleMs after the one before; the last one, the attachment,
    // comes later than settleMs after the page was ready — where a fixed wait would have read it.
    await pause(120);
    paintDescription(doc, "uno");
    await pause(120);
    paintDescription(doc, "uno dos");
    await pause(120);
    doc.querySelector("[data-late-slot]").insertAdjacentHTML("beforeend", late);
    const { doc: read } = await loading;
    const detail = dom.window.alfabetaExtract.readDetail(read);
    assert.equal(detail.attachments.length, 1);
    assert.equal(detail.description, "uno dos");
  } finally {
    dom.window.close();
  }
});

test("time with the tab hidden does not count towards settling: what paints after it is read", { timeout: 5000 }, async () => {
  const { html, late } = lateAttachment();
  const dom = framed(html);
  const main = dom.window.document;
  let state = "visible";
  Object.defineProperty(main, "visibilityState", { get: () => state });
  try {
    let done = false;
    const loading = dom.window.alfabetaExtract.iframeLoader(dom.window, FAST)(DETAIL).then((r) => { done = true; return r; });
    const doc = await whenReady(dom);
    state = "hidden"; // Chrome all but stops a hidden tab's frames
    await pause(FAST.settleMs * 3);
    assert.equal(done, false);
    doc.querySelector("[data-late-slot]").insertAdjacentHTML("beforeend", late); // painted once shown
    state = "visible";
    const { doc: read } = await loading;
    assert.equal(dom.window.alfabetaExtract.readDetail(read).attachments.length, 1);
  } finally {
    dom.window.close();
  }
});

test("a page that never holds still is unsettled, a failed load", { timeout: 5000 }, async () => {
  const dom = framed(lateAttachment().html);
  let changer = null;
  try {
    const loading = dom.window.alfabetaExtract.iframeLoader(dom.window, { ...FAST, settleCapMs: 500 })(DETAIL);
    const outcome = loading.then(() => "loaded", (err) => err.message);
    const doc = await whenReady(dom);
    let n = 0;
    changer = setInterval(() => paintDescription(doc, `cambio ${n++}`), 50);
    assert.equal(await outcome, "unsettled");
  } finally {
    clearInterval(changer);
    dom.window.close();
  }
});

// Chrome barely runs a hidden tab's timers (about once a second, then once a minute), so the poll
// after the tab is shown again may come long after the last one. That gap is time spent hidden: it
// must not count as time the page held still. A clock and a scheduler driven by hand show it.
test("the gap of a throttled hidden tab does not count as holding still", { timeout: 5000 }, async () => {
  const dom = framed(page("material-detail").serialize());
  const win = dom.window;
  let clock = 1_000_000;
  let tick = null;
  win.Date.now = () => clock;
  win.setInterval = (fn) => { tick = fn; return 1; };
  win.clearInterval = () => { tick = null; };
  let state = "visible";
  Object.defineProperty(win.document, "visibilityState", { get: () => state });
  try {
    let done = false;
    const loading = win.alfabetaExtract.iframeLoader(win, { timeoutMs: 120000, attempts: 1, settleMs: 1500, settleCapMs: 10000 })(DETAIL)
      .then((r) => { done = true; return r; });
    await whenReady(dom);
    const poll = async (ms) => { clock += ms; if (tick) tick(); await pause(0); };
    await poll(300); // ready, on screen
    state = "hidden";
    await poll(300);
    await poll(60000); // one throttled timer a minute later
    state = "visible"; // shown half a minute after that timer, before the next one
    await poll(30000); // the first poll on screen: those 30 s were spent hidden, not holding still
    assert.equal(done, false);
    for (let i = 0; i < 4; i++) await poll(300);
    assert.equal(done, false); // 1200 ms on screen
    await poll(300);
    assert.equal(done, true); // 1500 ms on screen
    await loading;
  } finally {
    dom.window.close();
  }
});

test("stillness before the tab was hidden does not carry over: 1.5 s unbroken once it is shown", { timeout: 5000 }, async () => {
  const dom = framed(page("material-detail").serialize());
  const win = dom.window;
  let clock = 1_000_000;
  let tick = null;
  win.Date.now = () => clock;
  win.setInterval = (fn) => { tick = fn; return 1; };
  win.clearInterval = () => { tick = null; };
  let state = "visible";
  Object.defineProperty(win.document, "visibilityState", { get: () => state });
  try {
    let done = false;
    const loading = win.alfabetaExtract.iframeLoader(win, { timeoutMs: 40000, attempts: 1, settleMs: 1500, settleCapMs: 10000 })(DETAIL)
      .then(() => { done = true; return "loaded"; }, (err) => err.message);
    await whenReady(dom);
    const poll = async (ms) => { clock += ms; if (tick) tick(); await pause(0); };
    for (let i = 0; i < 5; i++) await poll(300); // ready, then 1200 ms still on screen
    assert.equal(done, false);
    state = "hidden";
    await poll(60000); // a minute hidden: longer than the 40 s timeout
    state = "visible";
    await poll(300); // back on screen: neither timed out nor taken at once
    assert.equal(done, false);
    for (let i = 0; i < 4; i++) await poll(300);
    assert.equal(done, false); // 1200 ms on screen since it was shown
    await poll(300);
    assert.equal(await loading, "loaded");
  } finally {
    dom.window.close();
  }
});

// «Ver más publicaciones» (#288; spec 006 research S17): a topic shows its first 10 items and the
// button; a topic with no more keeps the button with an ancestor at `display: none`, as measured.
const CLASSWORK = "/u/5/w/synth-1/t/all";
const MORE_FAST = { ...FAST, moreTimeoutMs: 400 };
const row = (n) => `<li data-stream-item-type="5" data-stream-item-id="${9100 + n}"><span class="Vu2fZd">Material ${n}</span><div>Publicado: 1 oct</div></li>`;
const rows = (from, to) => Array.from({ length: to - from }, (_, i) => row(from + i)).join("");
const topic = (id, items, shown) => `<div role="region" data-topic-id="${id}"><h2>Tema ${id}</h2><ol>${items}</ol>`
  + `<div class="Mvr5Ef"><div style="${shown ? "" : "display: none;"}"><div><button jsname="t6Kl7b" aria-label="Ver más publicaciones">`
  + `<span aria-hidden="true">Ver más</span></button></div></div></div></div>`;
const classworkPage = () => `<html><body><h1>Trabajo de clase</h1>${topic("t1", rows(0, 10), true)}${topic("t2", rows(50, 52), false)}</body></html>`;

// The frame's «Trabajo de clase» once it has rows, with a count of the presses on each topic's button.
async function classworkReady(dom) {
  for (;;) {
    const frame = dom.window.document.querySelector("iframe");
    const doc = frame && frame.contentDocument;
    if (doc && doc.location.href !== "about:blank" && doc.body && doc.querySelector("li[data-stream-item-type]")) {
      const presses = { t1: 0, t2: 0 };
      for (const id of ["t1", "t2"]) {
        doc.querySelector(`[data-topic-id="${id}"] button`).addEventListener("click", () => { presses[id] += 1; });
      }
      return { doc, presses };
    }
    await pause(2);
  }
}

// What the page does on a press of t1's button: add rows after a moment, and hide it or not.
function answer(doc, { add, hide, after = 60 }) {
  const button = doc.querySelector('[data-topic-id="t1"] button');
  let next = 10;
  button.addEventListener("click", () => setTimeout(() => {
    const n = typeof add === "function" ? add() : add;
    doc.querySelector('[data-topic-id="t1"] ol').insertAdjacentHTML("beforeend", rows(next, next + n));
    next += n;
    if (typeof hide === "function" ? hide() : hide) button.parentElement.parentElement.setAttribute("style", "display: none;");
  }, after));
}

const perTopic = (X, doc) => {
  const out = {};
  for (const item of X.readClasswork(doc).items) out[item.topic] = (out[item.topic] || 0) + 1;
  return out;
};

test("a topic that shows «Ver más publicaciones» is read whole: one press, its last 3 items in", { timeout: 5000 }, async () => {
  const dom = framed(classworkPage(), CLASSWORK);
  try {
    const X = dom.window.alfabetaExtract;
    const loading = X.iframeLoader(dom.window, MORE_FAST)(CLASSWORK);
    const { doc, presses } = await classworkReady(dom);
    answer(doc, { add: 3, hide: true });
    const { doc: read } = await loading;
    assert.deepEqual(perTopic(X, read), { t1: 13, t2: 2 });
    assert.deepEqual(presses, { t1: 1, t2: 0 }); // the hidden one is never pressed
  } finally {
    dom.window.close();
  }
});

test("a topic past 20 items is pressed until it no longer shows the button", { timeout: 5000 }, async () => {
  const dom = framed(classworkPage(), CLASSWORK);
  try {
    const X = dom.window.alfabetaExtract;
    const loading = X.iframeLoader(dom.window, MORE_FAST)(CLASSWORK);
    const { doc, presses } = await classworkReady(dom);
    let n = 0;
    answer(doc, { add: () => (++n === 1 ? 10 : 2), hide: () => n === 2 });
    const { doc: read } = await loading;
    assert.deepEqual(perTopic(X, read), { t1: 22, t2: 2 });
    assert.equal(presses.t1, 2);
  } finally {
    dom.window.close();
  }
});

test("two topics that show the button are each pressed: the second is not taken for the first's answer", { timeout: 5000 }, async () => {
  const both = classworkPage().replace('<div style="display: none;">', '<div style="">');
  const dom = framed(both, CLASSWORK);
  try {
    const X = dom.window.alfabetaExtract;
    const loading = X.iframeLoader(dom.window, MORE_FAST)(CLASSWORK);
    const { doc, presses } = await classworkReady(dom);
    answer(doc, { add: 3, hide: true });
    const second = doc.querySelector('[data-topic-id="t2"] button');
    second.addEventListener("click", () => setTimeout(() => {
      doc.querySelector('[data-topic-id="t2"] ol').insertAdjacentHTML("beforeend", rows(60, 61));
      second.parentElement.parentElement.setAttribute("style", "display: none;");
    }, 60));
    const { doc: read } = await loading;
    assert.deepEqual(perTopic(X, read), { t1: 13, t2: 3 });
    assert.deepEqual(presses, { t1: 1, t2: 1 });
  } finally {
    dom.window.close();
  }
});

test("a button hidden at once, its rows after settleMs, is waited for: the rows are in", { timeout: 5000 }, async () => {
  const dom = framed(classworkPage(), CLASSWORK);
  try {
    const X = dom.window.alfabetaExtract;
    const loading = X.iframeLoader(dom.window, { ...MORE_FAST, moreTimeoutMs: 2000 })(CLASSWORK);
    const { doc } = await classworkReady(dom);
    const button = doc.querySelector('[data-topic-id="t1"] button');
    button.addEventListener("click", () => {
      button.parentElement.parentElement.setAttribute("style", "display: none;"); // a loading state
      setTimeout(() => doc.querySelector('[data-topic-id="t1"] ol').insertAdjacentHTML("beforeend", rows(10, 13)), MORE_FAST.settleMs * 3);
    });
    const { doc: read } = await loading;
    assert.deepEqual(perTopic(X, read), { t1: 13, t2: 2 });
  } finally {
    dom.window.close();
  }
});

test("a button drawn again before its rows come is no answer: the rows are in", { timeout: 5000 }, async () => {
  const dom = framed(classworkPage(), CLASSWORK);
  try {
    const X = dom.window.alfabetaExtract;
    const loading = X.iframeLoader(dom.window, { ...MORE_FAST, moreTimeoutMs: 2000 })(CLASSWORK);
    const { doc } = await classworkReady(dom);
    const button = doc.querySelector('[data-topic-id="t1"] button');
    button.addEventListener("click", () => {
      button.replaceWith(button.cloneNode(true)); // a fresh node, still shown, with no listener
      setTimeout(() => {
        doc.querySelector('[data-topic-id="t1"] ol').insertAdjacentHTML("beforeend", rows(10, 12));
        doc.querySelector('[data-topic-id="t1"] .Mvr5Ef > div').setAttribute("style", "display: none;");
      }, MORE_FAST.settleMs * 3);
    });
    const { doc: read } = await loading;
    assert.deepEqual(perTopic(X, read), { t1: 12, t2: 2 });
  } finally {
    dom.window.close();
  }
});

test("a press that only hides its button, with no new row, is a failed load, never a list read as whole", { timeout: 5000 }, async () => {
  const dom = framed(classworkPage(), CLASSWORK);
  try {
    const X = dom.window.alfabetaExtract;
    const outcome = X.iframeLoader(dom.window, MORE_FAST)(CLASSWORK).then(() => "loaded", (err) => err.message);
    const { doc } = await classworkReady(dom);
    answer(doc, { add: 0, hide: true });
    assert.equal(await outcome, "more_unanswered");
  } finally {
    dom.window.close();
  }
});

test("a press the page does not answer is a failed load, never a list read as whole", { timeout: 5000 }, async () => {
  const dom = framed(classworkPage(), CLASSWORK);
  try {
    const X = dom.window.alfabetaExtract;
    const outcome = X.iframeLoader(dom.window, MORE_FAST)(CLASSWORK).then(() => "loaded", (err) => err.message);
    await classworkReady(dom);
    assert.equal(await outcome, "more_unanswered");
  } finally {
    dom.window.close();
  }
});

test("a button still shown after maxPresses is a failed load", { timeout: 5000 }, async () => {
  const dom = framed(classworkPage(), CLASSWORK);
  try {
    const X = dom.window.alfabetaExtract;
    const outcome = X.iframeLoader(dom.window, { ...MORE_FAST, maxPresses: 3 })(CLASSWORK).then(() => "loaded", (err) => err.message);
    const { doc, presses } = await classworkReady(dom);
    answer(doc, { add: 1, hide: false });
    assert.equal(await outcome, "more_endless");
    assert.equal(presses.t1, 3);
  } finally {
    dom.window.close();
  }
});

test("only «Trabajo de clase» is pressed: the button on another page is left alone", { timeout: 5000 }, async () => {
  const detail = page("material-detail");
  detail.window.document.body.insertAdjacentHTML("beforeend", '<div><button jsname="t6Kl7b" aria-label="Ver más publicaciones">Ver más</button></div>');
  const dom = framed(detail.serialize());
  try {
    const X = dom.window.alfabetaExtract;
    const loading = X.iframeLoader(dom.window, MORE_FAST)(DETAIL);
    const doc = await whenReady(dom);
    let pressed = 0;
    doc.querySelector('button[jsname="t6Kl7b"]').addEventListener("click", () => { pressed += 1; });
    await loading;
    assert.equal(pressed, 0);
  } finally {
    dom.window.close();
  }
});

test("the button is found by its name or by its label, and not when an ancestor hides it", () => {
  const X = extract;
  const dom = new JSDOM(`<body>${topic("t1", rows(0, 10), true)}</body>`);
  const doc = dom.window.document;
  assert.ok(X.shownMore(doc));
  doc.querySelector("button").removeAttribute("jsname");
  assert.ok(X.shownMore(doc), "by its label");
  doc.querySelector("button").setAttribute("jsname", "t6Kl7b");
  doc.querySelector("button").setAttribute("aria-label", "Show more");
  assert.ok(X.shownMore(doc), "by its name");
  doc.querySelector(".Mvr5Ef > div").setAttribute("style", "display: none;");
  assert.equal(X.shownMore(doc), null);
  doc.querySelector(".Mvr5Ef > div").setAttribute("style", "");
  doc.querySelector(".Mvr5Ef").hidden = true;
  assert.equal(X.shownMore(doc), null);
});

// The stream past its first load (#293; spec 006 research S17): scrolled to its bottom, it loads
// older posts; the loader scrolls until none come within streamWaitMs.
const STREAM = "/u/5/c/synth-1";
const STREAM_FAST = { ...FAST, streamWaitMs: 300 };
const post = (n) => `<div data-stream-item-id="${8100 + n}"><h2>Autor inventado</h2><div class="pco8Kc">Anuncio ${n}</div>`
  + `<div>Fecha de creación: ${1 + (n % 28)} sept</div></div>`;
const posts = (from, to) => Array.from({ length: to - from }, (_, i) => post(from + i)).join("");
const streamPage = (n) => `<html><body><h1>Tablón</h1><main id="feed">${posts(0, n)}</main></body></html>`;

// The frame's stream once it has posts, its scrolls counted and answered by `onScroll`.
async function streamReady(dom, onScroll) {
  for (;;) {
    const frame = dom.window.document.querySelector("iframe");
    const doc = frame && frame.contentDocument;
    if (doc && doc.location.href !== "about:blank" && doc.body && doc.querySelector("[data-stream-item-id]")) {
      const seen = { scrolls: 0 };
      frame.contentWindow.scrollTo = () => { seen.scrolls += 1; onScroll(doc, seen.scrolls); };
      return seen;
    }
    await pause(2);
  }
}

test("the stream is scrolled until no older post comes: every announcement is read", { timeout: 5000 }, async () => {
  const dom = framed(streamPage(5), STREAM);
  try {
    const X = dom.window.alfabetaExtract;
    const loading = X.iframeLoader(dom.window, STREAM_FAST)(STREAM);
    const loads = [[5, 9], [9, 12]]; // two scrolls bring older posts, the third none
    const seen = await streamReady(dom, (doc, n) => {
      const next = loads[n - 1];
      if (next) setTimeout(() => doc.getElementById("feed").insertAdjacentHTML("beforeend", posts(...next)), 60);
    });
    const { doc } = await loading;
    assert.equal(X.readStream(doc).length, 12);
    assert.equal(seen.scrolls, 3);
  } finally {
    dom.window.close();
  }
});

test("older posts that come late, within streamWaitMs, are still waited for", { timeout: 5000 }, async () => {
  const dom = framed(streamPage(5), STREAM);
  try {
    const X = dom.window.alfabetaExtract;
    const loading = X.iframeLoader(dom.window, { ...STREAM_FAST, streamWaitMs: 1200 })(STREAM);
    await streamReady(dom, (doc, n) => {
      if (n === 1) setTimeout(() => doc.getElementById("feed").insertAdjacentHTML("beforeend", posts(5, 7)), FAST.settleMs * 4);
    });
    const { doc } = await loading;
    assert.equal(X.readStream(doc).length, 7);
  } finally {
    dom.window.close();
  }
});

test("a stream that never ends is a failed load, never read as whole", { timeout: 5000 }, async () => {
  const dom = framed(streamPage(5), STREAM);
  try {
    const X = dom.window.alfabetaExtract;
    const outcome = X.iframeLoader(dom.window, { ...STREAM_FAST, maxScrolls: 3 })(STREAM).then(() => "loaded", (err) => err.message);
    let next = 5;
    await streamReady(dom, (doc) => {
      setTimeout(() => { doc.getElementById("feed").insertAdjacentHTML("beforeend", posts(next, next + 1)); next += 1; }, 30);
    });
    assert.equal(await outcome, "stream_endless");
  } finally {
    dom.window.close();
  }
});

test("only the stream is scrolled: «Trabajo de clase» and an item page are not", { timeout: 5000 }, async () => {
  for (const [html, path] of [[classworkPage().replace('<div style="">', '<div style="display: none;">'), CLASSWORK], [page("material-detail").serialize(), DETAIL]]) {
    const dom = framed(html, path);
    try {
      const X = dom.window.alfabetaExtract;
      const loading = X.iframeLoader(dom.window, STREAM_FAST)(path);
      let scrolls = 0;
      for (;;) {
        const frame = dom.window.document.querySelector("iframe");
        if (frame && frame.contentDocument && frame.contentDocument.body && frame.contentDocument.location.href !== "about:blank") {
          frame.contentWindow.scrollTo = () => { scrolls += 1; };
          break;
        }
        await pause(2);
      }
      await loading;
      assert.equal(scrolls, 0, path);
    } finally {
      dom.window.close();
    }
  }
});
