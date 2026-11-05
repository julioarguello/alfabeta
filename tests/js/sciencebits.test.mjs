// Science Bits discovery and capture over a synthetic unit page (2026-11-05: what the teacher shows differs by
// language and by lesson; a hidden lesson and an assessment are never opened, and one hidden lesson stops nothing).
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { JSDOM } from "jsdom";

const SCRIPTS = new URL("../../skills/sciencebits-a-notebooklm/scripts/", import.meta.url);
const DISCOVER = fs.readFileSync(new URL("discover_lessons.js", SCRIPTS), "utf8");
const ORCHESTRATOR = fs.readFileSync(new URL("orchestrator.js", SCRIPTS), "utf8");
const UNIT_PAGE = fs.readFileSync(new URL("../fixtures/sciencebits/unit.html", import.meta.url), "utf8");
const ORIGIN = "https://sb.invalid";
const CLASSES = `<body>
  <div class="box-center-unidad col"><a class="btn-acceder" href="${ORIGIN}/intranet/es/myclasses/unit?code=aa">x</a>Unidad inventada Materia</div>
  <div class="box-center-unidad col leccion-bloqueada"><a class="btn-acceder desactivado" href="">x</a>Unidad oculta Materia</div>
</body>`;

// jsdom's arrays and objects belong to another realm, which deepEqual tells apart.
const plain = (value) => JSON.parse(JSON.stringify(value));

// Timers run at once, so a test takes no real time; the page's own order of events is kept.
function fast(window) {
  window.setTimeout = (fn) => { setImmediate(fn); return 0; };
}

// The classes page, whose iframes load `pages[lang]`: a synthetic page, a login, or nothing shown.
function classesPage(pages) {
  const dom = new JSDOM(CLASSES, { url: `${ORIGIN}/intranet/es/myclasses/index`, runScripts: "outside-only" });
  const { window } = dom;
  fast(window);
  const frames = [];
  const create = window.document.createElement.bind(window.document);
  window.document.createElement = (tag) => {
    if (tag !== "iframe") return create(tag);
    const frame = { style: {}, remove() {}, clicks: [] };
    Object.defineProperty(frame, "src", {
      set(url) {
        const lang = url.match(/\/intranet\/([a-z]+)\//)[1];
        const inner = new JSDOM(pages[lang] ?? "<body></body>", {
          url: pages[lang] === "login" ? `${ORIGIN}/login/` : url,
          runScripts: "outside-only",
        });
        const reached = (code) => {
          frame.clicks.push(code);
          inner.window.open(`/intranet/${lang}/mylesson/index?sem=sem${lang}&code=${code}`);
        };
        inner.window.verleccion1 = reached;
        for (const button of inner.window.document.querySelectorAll('[onclick^="verleccion1"]')) {
          const code = button.getAttribute("onclick").match(/'(.*)'/)[1];
          button.removeAttribute("onclick");
          button.setAttribute("onclick", `verleccion1("${code}")`);
          button.click = () => reached(code);
        }
        frame.contentWindow = inner.window;
        frame.contentDocument = inner.window.document;
        frames.push(frame);
        setImmediate(() => frame.onload());
      },
    });
    return frame;
  };
  window.document.body.appendChild = () => {};
  return { window, frames };
}

async function discover(pages, name = "Unidad inventada", langs = ["es", "en"]) {
  const { window, frames } = classesPage(pages);
  window.__UNIT = { name, langs };
  const report = plain(await window.eval(DISCOVER));
  return { report, window, frames };
}

test("only the lessons the teacher shows are queued, and only they are clicked", async () => {
  const { report, window, frames } = await discover({ es: UNIT_PAGE });
  assert.deepEqual(plain(frames[0].clicks), ["6c315f6573263d31", "6c325f6573263d31"]);
  assert.deepEqual(report.langs.es.lessons, ["Primera lección Materia Explicamos 1", "Segunda lección Materia Explicamos 2"]);
  assert.deepEqual(report.langs.es.hidden, ["Lección oculta Materia Empezamos"]);
  assert.deepEqual(report.langs.es.assessments, ["Evaluación: unidad inventada Materia Evaluamos"]);
  assert.deepEqual(
    plain(window.__SB.queue.map((q) => [q.lang, q.id, q.sem, q.code])),
    [
      ["es", "L1", "semes", "6c315f6573263d31"],
      ["es", "L2", "semes", "6c325f6573263d31"],
    ],
  );
});

test("a language that shows no lessons queues nothing and the others go on", async () => {
  const { report, window } = await discover({ es: UNIT_PAGE });
  assert.deepEqual(report.langs.en, { lessons: [], hidden: [], assessments: [] });
  assert.equal(report.queued, 2);
  assert.ok(window.__SB.queue.every((q) => q.lang === "es"));
});

test("the result never carries sem or code, which the extension blanks", async () => {
  const { report } = await discover({ es: UNIT_PAGE });
  assert.doesNotMatch(JSON.stringify(report), /semes|6c31/);
});

test("the unit is looked up among the ones shown: hidden or ambiguous stops before any page opens", async () => {
  const hidden = await discover({}, "Unidad oculta");
  assert.equal(hidden.report.error, "unit_not_shown_on_this_page");
  assert.equal(hidden.frames.length, 0);
  assert.equal(hidden.window.__SB, undefined);
  const both = classesPage({});
  both.window.document.body.insertAdjacentHTML(
    "beforeend",
    `<div class="box-center-unidad col"><a class="btn-acceder" href="${ORIGIN}/intranet/es/myclasses/unit?code=bb">x</a>Unidad inventada dos</div>`,
  );
  both.window.__UNIT = { name: "Unidad inventada", langs: ["es"] };
  assert.equal((await both.window.eval(DISCOVER)).error, "ambiguous_unit");
});

test("an expired session stops the discovery and queues nothing", async () => {
  const { report, window } = await discover({ es: "login" });
  assert.deepEqual(report, { error: "SESSION_EXPIRED", lang: "es" });
  assert.equal(window.__SB, undefined);
});

// The capture: each lesson's iframe either says it is hidden or finishes its job at once.
function capturePage(hiddenCodes) {
  const dom = new JSDOM("<body></body>", { url: `${ORIGIN}/intranet/es/myclasses/index`, runScripts: "outside-only" });
  const { window } = dom;
  fast(window);
  const loaded = [];
  const create = window.document.createElement.bind(window.document);
  window.document.createElement = (tag) => {
    if (tag !== "iframe") return create(tag);
    const frame = { style: {}, remove() {} };
    Object.defineProperty(frame, "src", {
      set(url) {
        const code = new URL(url, ORIGIN).searchParams.get("code");
        loaded.push(url);
        const hidden = hiddenCodes.includes(code);
        frame.contentWindow = {
          location: { href: `${ORIGIN}${url}&refreshed=true` },
          eval() { this.__job = { done: true, n: 3, size: 10, log: [] }; },
        };
        frame.contentDocument = {
          readyState: "complete",
          body: { innerText: hidden ? "Oculta por el docente" : "lección" },
          getElementById: () => ({}),
        };
      },
    });
    return frame;
  };
  window.document.body.appendChild = () => {};
  window.document.getElementById = () => null;
  return { window, loaded };
}

test("one lesson hidden since discovery is skipped and the rest of its language is captured", async () => {
  const { window, loaded } = capturePage(["c1"]);
  const queue = ["c1", "c2", "c3"].map((code, i) => ({ lang: "es", id: `L${i + 1}`, sem: "s", code, title: code }));
  window.__SB = { queue };
  assert.equal(window.eval(ORCHESTRATOR), "orchestrator started: 3");
  while (!window.__orch.done) await new Promise((r) => setImmediate(r));
  assert.deepEqual(
    plain(window.__orch.results.map((r) => [r.tag, r.n ?? null, r.err ?? null])),
    [
      ["es_L1", null, "HIDDEN"],
      ["es_L2", 3, null],
      ["es_L3", 3, null],
    ],
  );
  assert.equal(loaded.length, 3); // a hidden lesson is not retried
  assert.match(loaded[1], /^\/intranet\/es\/mylesson\/index\?sem=s&code=c2$/);
});
