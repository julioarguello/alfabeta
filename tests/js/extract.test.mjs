// The extractor over the synthetic pages (spec 001 T032, T033; research R11).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { JSDOM } from "jsdom";

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
