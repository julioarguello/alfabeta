// Classroom extractor (spec 001 T036, research R3, contracts/capture.schema.json).
//
// Injected by the skill into the Classroom tab of the school account. It only reads: it loads the
// pages FR-007 allows (home, «Trabajo de clase», the stream, and the detail of assignments,
// materials and questions) in a hidden same-origin iframe, never navigates the tab, never submits,
// never opens a form or a quiz, and waits at least 2 s with jitter between pages. It presses one
// button only: a topic's «Ver más publicaciones» on «Trabajo de clase», which shows the items past
// the topic's first 10 and changes nothing (#288). It scrolls one page only: the stream, to its
// bottom, until no older post comes (#293).
// It returns the texts exactly as shown; Python interprets them (dates, statuses, categories).
//
// Two layers: pure readers (a document in, contract-shaped data out) and a driver whose page
// loader, clock and download are injected, so the tests run it on synthetic pages.
(function (root) {
  "use strict";

  const VERSION = 1;
  const MIN_WAIT_MS = 2000;
  const JITTER_MS = 1000;
  // data-stream-item-type on «Trabajo de clase» rows (research R3, S3).
  const ITEM_TYPES = { 1: "assignment", 5: "material", 2: "question" };
  const DETAIL_ROUTE = { assignment: "a", material: "m", question: "mc" };
  // One label each page kind must show; without it the interface is not the one this was built on.
  const EXPECTED = {
    classwork: "Trabajo de clase",
    stream: "Tablón",
    assignment: "Tu trabajo",
    question: "Tu respuesta",
    material: "Comentarios de la clase",
  };
  const STATUS_WORDS = new Set([
    "Asignado", "Falta", "Entregado", "Entregado con retraso", "Calificado", "Devuelto",
    "Sin entregar", "Completada",
  ]);
  const PANEL_HEADINGS = new Set(["Tu trabajo", "Tu respuesta"]);
  const COMMENT_HEADINGS = new Set(["Comentarios de la clase", "Comentarios privados"]);
  const BUTTON_LABELS = new Set(["Añadir o crear", "Marcar como completado", "Entregar"]);
  const CHALLENGE = /tráfico inusual|demasiadas peticiones|unusual traffic|captcha/i;
  const MONTHS = "ene|feb|mar|abr|may|jun|jul|ago|sept|oct|nov|dic";
  // «Hoy» and «Ayer» too: an item posted the day before shows «Ayer» (first real run, 2026-10-27).
  const DATE = `(?:\\d{1,2} (?:${MONTHS})(?:, \\d{1,2}:\\d{2})?|\\d{1,2}:\\d{2}|Hoy|Ayer)`;
  const POSTED = new RegExp(`^(${DATE})(?:\\s*\\(Última modificación:\\s*(${DATE})\\))?$`);
  const NOTICE = /^(Tarea|Material|Pregunta): /;
  // An attachment's aria-label is «Archivo adjunto: <tipo>: <name>»; the name is the file's
  // (measured 2026-10-27 on the real pages, where every download would otherwise go unmatched).
  // An image on the stream came without the type: «Archivo adjunto: <name>» (2026-10-28).
  const ATTACHMENT_LABEL = /^Archivo adjunto: (?:[^:]+: )?/;
  // A topic of «Trabajo de clase» shows its first 10 items and, below them, this button for the rest;
  // a topic with no more keeps the button with an ancestor at `display: none`. Scrolling loads
  // nothing; one press loads the rest of a topic of 12 and of 13 (spec 006 research S17, 2026-11-24).
  // By its name or its label, so a renamed one of the two still finds it.
  const MORE_BUTTON = 'button[jsname="t6Kl7b"], button[aria-label="Ver más publicaciones"]';
  // A class with nothing in «Trabajo de clase» shows only this, and no rows (measured 2026-10-28).
  const EMPTY_CLASSWORK = /^Aún no hay tareas/;
  // And a class with no announcements shows this on its stream (measured 2026-10-28).
  const EMPTY_STREAM = /^Aquí se mostrarán novedades de esta clase/;
  // A stream post's class comments sit in this block inside the post (the anonymized stream page,
  // 2026-10-25): a link a classmate leaves there is not the announcement's attachment (FR-009).
  const STREAM_COMMENTS = ".s2g3Xd";

  const clean = (text) => (text || "").replace(/\s+/g, " ").trim();

  function texts(node) {
    const out = [];
    if (!node) return out;
    const walker = node.ownerDocument.createTreeWalker(node, 4);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const t = clean(n.textContent);
      if (t) out.push({ text: t, node: n });
    }
    return out;
  }

  // A description as the page lays it out: a <br> or a block ends a line, inline marks do not
  // (textContent ran «etxerako.Koadernoak» together on the real page, 2026-10-27).
  function blockText(el) {
    let out = "";
    const walk = (node) => {
      for (const child of node.childNodes) {
        if (child.nodeType === 3) out += child.nodeValue;
        else if (child.nodeName === "BR") out += "\n";
        else if (child.nodeType === 1) {
          const block = /^(DIV|P|LI|UL|OL)$/.test(child.nodeName);
          if (block) out += "\n";
          walk(child);
          if (block) out += "\n";
        }
      }
    };
    walk(el);
    return out.split("\n").map((line) => line.replace(/\s+/g, " ").trim()).join("\n").replace(/\n{3,}/g, "\n\n").trim();
  }

  function hasLabel(doc, label) {
    if (!doc.body) return false;
    if (texts(doc.body).some((t) => t.text === label)) return true;
    return [...doc.querySelectorAll("[aria-label]")].some((e) => clean(e.getAttribute("aria-label")) === label);
  }

  // A stop instead of data: a challenge, or the interface this extractor was built on is not there.
  function detectStop(doc, kind) {
    const body = doc.body ? doc.body.textContent : "";
    if (CHALLENGE.test(body) || doc.querySelector('iframe[title*="captcha" i]')) return "challenge";
    if (kind === "home") return classCards(doc).length ? null : "unexpected_ui";
    return hasLabel(doc, EXPECTED[kind]) ? null : "unexpected_ui";
  }

  function classCards(doc) {
    return [...doc.querySelectorAll("li")].filter(
      (li) => li.querySelector("h2, h3, [role=heading]") && classLink(li),
    );
  }

  function classLink(node) {
    return [...node.querySelectorAll("a[href]")].find((a) => /^\/u\/\d+\/c\/[^/?#]+$/.test(a.getAttribute("href")));
  }

  // The class list from the home page; the class id is the segment after /c/ in its link.
  function readClasses(doc, path) {
    const index = /^\/u\/(\d+)\//.exec(path || "");
    const seen = new Map();
    for (const card of classCards(doc)) {
      const id = classLink(card).getAttribute("href").split("/")[4];
      if (!seen.has(id)) seen.set(id, { id, title: clean(card.querySelector("h2, h3, [role=heading]").textContent), visibility: "visible" });
    }
    return { accountIndex: index ? Number(index[1]) : null, classes: [...seen.values()] };
  }

  function listingDate(row) {
    const found = texts(row).find((t) => /^(Fecha de entrega|Publicado|Sin fecha de entrega|Última modificación)/.test(t.text));
    return found ? found.text : "";
  }

  // Topics in order and the rows of «Trabajo de clase»; a row outside any topic is «Sin tema».
  function readClasswork(doc) {
    const topics = [];
    const regions = [...doc.querySelectorAll("[data-topic-id][role=region]")];
    regions.forEach((region, i) => {
      const heading = region.querySelector("h2, h3, [role=heading]");
      topics.push({ id: region.getAttribute("data-topic-id"), title: clean(heading && heading.textContent), order: i + 1 });
    });
    const rows = [...doc.querySelectorAll("li[data-stream-item-type]")].filter((r) => ITEM_TYPES[r.getAttribute("data-stream-item-type")]);
    const items = rows.map((row) => {
      const region = row.closest("[data-topic-id][role=region]");
      const title = row.querySelector("span.Vu2fZd");
      return {
        numericId: row.getAttribute("data-stream-item-id"),
        topic: region ? region.getAttribute("data-topic-id") : null,
        type: ITEM_TYPES[row.getAttribute("data-stream-item-type")],
        title: clean(title && title.textContent),
        listing_date_text: listingDate(row),
      };
    });
    if (items.some((i) => i.topic === null)) topics.push({ id: null, title: "Sin tema", order: topics.length + 1 });
    return { topics, items };
  }

  // One rule for Drive attachments, others for Google files, forms, videos and plain links.
  function attachmentOf(anchor) {
    const href = anchor.getAttribute("href") || "";
    let url;
    try { url = new URL(href, "https://classroom.google.com/"); } catch (_) { return null; }
    const host = url.hostname;
    const parts = url.pathname.split("/");
    const name = clean(anchor.getAttribute("aria-label") || anchor.getAttribute("title") || anchor.textContent).replace(ATTACHMENT_LABEL, "");
    if (host === "classroom.google.com" || (host === "drive.google.com" && parts[2] === "folders")) return null;
    if (host === "drive.google.com" && parts[1] === "file" && parts[2] === "d") return { id: parts[3], kind: "file", name };
    if (host === "drive.google.com" && url.searchParams.get("id")) return { id: url.searchParams.get("id"), kind: "file", name };
    if (host === "docs.google.com" && parts[1] === "forms") return { id: parts[3] || href, kind: "form", name };
    if (host === "docs.google.com" && parts[2] === "d") {
      const type = { document: "document", presentation: "presentation", spreadsheets: "spreadsheet" }[parts[1]] || null;
      return { id: parts[3], kind: "google_doc", google_type: type, name };
    }
    if (host === "forms.gle") return { id: href, kind: "form", name };
    if (host.endsWith("youtube.com") && url.searchParams.get("v")) return { id: url.searchParams.get("v"), kind: "video", name };
    if (host === "youtu.be") return { id: parts[1], kind: "video", name };
    if (url.protocol === "http:" || url.protocol === "https:") return { id: url.href, kind: "link", name };
    return null;
  }

  // `skip`: a selector whose elements hold no attachment (a post's comments).
  function attachmentsIn(nodes, skip = null) {
    const seen = new Map();
    for (const node of nodes) {
      for (const a of node.querySelectorAll ? node.querySelectorAll("a[href]") : []) {
        if (skip && a.closest(skip)) continue;
        const found = attachmentOf(a);
        if (found && !seen.has(found.id)) seen.set(found.id, found);
      }
    }
    return [...seen.values()];
  }

  // The «Tu trabajo» panel: the element whose heading is «Tu trabajo» or «Tu respuesta».
  function workPanel(main) {
    const heading = [...main.querySelectorAll("h2, h3, [role=heading]")].find((h) => PANEL_HEADINGS.has(clean(h.textContent)));
    return heading ? heading.closest("aside") || heading.parentElement.parentElement : null;
  }

  // Everything of the detail before the comments; the comments are never read (FR-009).
  function beforeComments(main) {
    const out = [];
    for (const t of texts(main)) {
      if (COMMENT_HEADINGS.has(t.text)) break;
      out.push(t);
    }
    return out;
  }

  // The detail's own region: [role=main] where there is one; a material page has none, so the
  // smallest element holding both the title and the comments heading.
  function commentsHeading(doc) {
    return [...doc.querySelectorAll("h2, h3")].find((h) => COMMENT_HEADINGS.has(clean(h.textContent)));
  }

  // The item's title: the last h1 before the comments (the app bar has its own h1, with the class).
  function itemTitle(doc) {
    const comments = commentsHeading(doc);
    const before = [...doc.querySelectorAll("h1")].filter((h) => !comments || h.compareDocumentPosition(comments) & 4);
    return before.at(-1) || null;
  }

  function detailRoot(doc) {
    const main = doc.querySelector("[role=main]");
    if (main) return main;
    const title = itemTitle(doc);
    const comments = commentsHeading(doc);
    if (!title || !comments) return doc.body;
    for (let node = title.parentElement; node; node = node.parentElement) {
      if (node.contains(comments)) return node;
    }
    return doc.body;
  }

  function readDetail(doc) {
    const main = detailRoot(doc);
    const panel = workPanel(main);
    const inPanel = (t) => panel && panel.contains(t.node);
    const own = beforeComments(main);
    const body = own.filter((t) => !inPanel(t));
    const posted = body.map((t) => POSTED.exec(t.text)).find(Boolean);
    const due = body.find((t) => t.text.startsWith("Fecha de entrega") || t.text === "Sin fecha de entrega");
    const points = body.find((t) => /^\d+ puntos$/.test(t.text));
    const panelTexts = own.filter(inPanel);
    // A question's status («Sin entregar») sits outside the block under «Tu respuesta».
    let status = panelTexts.find((t) => STATUS_WORDS.has(t.text)) || own.find((t) => STATUS_WORDS.has(t.text));
    if (!status && panelTexts.length) {
      const after = panelTexts.findIndex((t) => PANEL_HEADINGS.has(t.text));
      status = panelTexts.slice(after + 1).find((t) => !BUTTON_LABELS.has(t.text));
    }
    const notice = own.find((t) => /falta esto/i.test(t.text));
    const grade = panelTexts.find((t) => /^\d+([.,]\d+)?\s*\/\s*\d+$/.test(t.text));
    const description = [...main.querySelectorAll(".nGi02b")].map(blockText).join("\n");
    const bodyNodes = [...main.children].filter((e) => !(panel && (e === panel || e.contains(panel) || panel.contains(e))));
    const attachmentNodes = bodyNodes.length ? bodyNodes : [main];
    const commentsStart = own.length < texts(main).length ? texts(main)[own.length].node : null;
    const beforeTheComments = (a) => !commentsStart || (a.compareDocumentPosition(commentsStart) & 4);
    // The page's own bar (account, apps) comes before the title; an attachment comes after it.
    const title = itemTitle(doc);
    const afterTheTitle = (a) => !title || (title.compareDocumentPosition(a) & 4);
    const attachments = attachmentsIn(attachmentNodes).filter((x) => {
      const anchor = [...main.querySelectorAll("a[href]")].find((a) => (attachmentOf(a) || {}).id === x.id);
      return anchor && afterTheTitle(anchor) && beforeTheComments(anchor) && !(panel && panel.contains(anchor));
    });
    return {
      posted_text: posted ? posted[1] : "",
      modified_text: posted && posted[2] ? `Última modificación: ${posted[2]}` : null,
      due_text: due ? due.text : null,
      points: points ? points.text : null,
      description,
      status_text: status ? status.text : null,
      status_notice_text: notice ? notice.text : null,
      grade_text: grade ? grade.text : null,
      returned_text: null,
      teacher_comment: null,
      attachments,
      submission: panel ? attachmentsIn([panel]) : [],
    };
  }

  // Announcements of the stream; the notices of new items are skipped (they are in «Trabajo de clase»).
  // The text is the post's own block, line by line: its header names the author, and every post
  // hides a teacher-only notice in a tooltip, longer than any line of the body (measured 2026-10-28).
  function readStream(doc) {
    const created = (p) => texts(p).find((t) => t.text.startsWith("Fecha de creación"));
    // A notice says «Tarea: …» in its heading; an announcement's heading names its author, and its
    // body or a comment may start with «Tarea: » too.
    const notice = (p) => NOTICE.test(clean(p.querySelector("h2") && p.querySelector("h2").textContent));
    const posts = [...doc.querySelectorAll("[data-stream-item-id]")].filter(created);
    return posts
      .filter((p) => !notice(p))
      .map((p) => {
        const body = p.querySelector(".pco8Kc");
        return {
          id: p.getAttribute("data-stream-item-id"),
          // The label and its date can be text nodes of their own (measured 2026-10-28).
          created_text: clean(created(p).node.parentElement.textContent),
          text: body ? blockText(body) : "",
          attachments: attachmentsIn([p], STREAM_COMMENTS),
        };
      });
  }

  function base64(text) {
    return (typeof btoa === "function" ? btoa(text) : Buffer.from(text).toString("base64")).replace(/=+$/, "");
  }

  function stamp(date) {
    return date.toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
  }

  function stop(run, now, reason, classId) {
    const capture = { version: VERSION, type: "stop", run, captured_at: now().toISOString(), reason };
    if (classId) capture.class = classId;
    return capture;
  }

  function captureClasses({ run, doc, path, now }) {
    const reason = detectStop(doc, "home");
    if (reason) return stop(run, now, reason);
    const { accountIndex, classes } = readClasses(doc, path);
    return { version: VERSION, type: "classes", run, captured_at: now().toISOString(), account_index: accountIndex, classes };
  }

  // One class: «Trabajo de clase», each item's detail, the stream. `load(path)` returns {doc, path}.
  // The loader throws this when a page lands on Google's sign-in: the school session expired.
  class SessionExpired extends Error {
    constructor() { super("session_expired"); this.name = "SessionExpired"; }
  }

  async function captureClass({ run, classId, title, account, load, sleep, now, random }) {
    let last = null;
    const visit = async (path) => {
      if (last !== null) {
        const waited = now().getTime() - last;
        const wanted = MIN_WAIT_MS + Math.floor(random() * JITTER_MS);
        if (waited < wanted) await sleep(wanted - waited);
      }
      const page = await load(path);
      last = now().getTime();
      return page;
    };
    let classwork;
    try {
      classwork = await visit(`/u/${account}/w/${classId}/t/all`);
    } catch (err) {
      if (err && err.name === "SessionExpired") return stop(run, now, "session_expired", classId);
      throw err;
    }
    let reason = detectStop(classwork.doc, "classwork");
    if (reason) return stop(run, now, reason, classId);
    let listing = readClasswork(classwork.doc);
    if (!listing.items.length) {
      // An empty listing is read once more, so a page still filling in is not taken for an empty class.
      try {
        classwork = await visit(`/u/${account}/w/${classId}/t/all`);
      } catch (err) {
        if (err && err.name === "SessionExpired") return stop(run, now, "session_expired", classId);
        throw err;
      }
      reason = detectStop(classwork.doc, "classwork");
      if (reason) return stop(run, now, reason, classId);
      listing = readClasswork(classwork.doc);
    }
    const items = [];
    let complete = true;
    for (const row of listing.items) {
      const route = DETAIL_ROUTE[row.type];
      let page;
      try {
        page = await visit(`/u/${account}/c/${classId}/${route}/${base64(row.numericId)}/details`);
      } catch (err) {
        if (err && err.name === "SessionExpired") return stop(run, now, "session_expired", classId);
        complete = false; // a page that does not load: this capture is incomplete and withdraws nothing
        continue;
      }
      reason = detectStop(page.doc, row.type);
      if (reason) return stop(run, now, reason, classId);
      const id = page.path.split("/")[6]; // /u/<n>/c/<class>/<a|m|mc>/<item>/details
      if (!id) { complete = false; continue; }
      items.push({ id, topic: row.topic, type: row.type, title: row.title, listing_date_text: row.listing_date_text, detail: readDetail(page.doc) });
    }
    let streamPage = null;
    try {
      streamPage = await visit(`/u/${account}/c/${classId}`);
    } catch (err) {
      if (err && err.name === "SessionExpired") return stop(run, now, "session_expired", classId);
      complete = false;
    }
    if (streamPage) {
      reason = detectStop(streamPage.doc, "stream");
      if (reason) return stop(run, now, reason, classId);
    }
    return {
      version: VERSION, type: "class", run, captured_at: now().toISOString(), complete,
      class: { id: classId, title: title || "" }, topics: listing.topics, items, stream: streamPage ? readStream(streamPage.doc) : [],
    };
  }

  // When a page is ready to read: its rows, its title and date, or its posts. The iframe's own `load`
  // event is not waited for: on Classroom it came more than 30 s after the content (2026-10-27).
  function pageReady(path, doc) {
    if (/\/w\/[^/]+\/t\/all$/.test(path)) {
      return !!doc.querySelector("li[data-stream-item-type]") || texts(doc.body).some((t) => EMPTY_CLASSWORK.test(t.text));
    }
    if (/\/details$/.test(path)) {
      return doc.querySelectorAll("h1").length >= 2 && texts(doc.body).some((t) => new RegExp(`^${DATE}`).test(t.text));
    }
    return !!doc.querySelector("[data-stream-item-id]") || texts(doc.body).some((t) => EMPTY_STREAM.test(t.text));
  }

  // While the tab is not on screen Chrome all but stops its frames: a page took minutes and most
  // timed out, until the session itself expired (2026-10-28). So nothing loads while it is hidden.
  function whileHidden(win) {
    const doc = win.document;
    return new Promise((resolve) => {
      if (doc.visibilityState !== "hidden") return resolve();
      const shown = () => {
        if (doc.visibilityState === "hidden") return;
        doc.removeEventListener("visibilitychange", shown);
        resolve();
      };
      doc.addEventListener("visibilitychange", shown);
    });
  }

  // What a page shows, as the capture reads it: a page is read once this has held still. On
  // 2026-11-10 two classes were read while their item pages were still painting — two items without
  // their attachments, two without their points and status — and the pages were taken as ready.
  function pageReading(path, doc) {
    try {
      if (/\/details$/.test(path)) return JSON.stringify(readDetail(doc));
      if (/\/w\/[^/]+\/t\/all$/.test(path)) return JSON.stringify(readClasswork(doc));
      return JSON.stringify(readStream(doc));
    } catch (_) {
      return null;
    }
  }

  // Whether a button is on the page and shown: not hidden, nor inside anything hidden.
  function isShown(button) {
    const doc = button.ownerDocument;
    if (!doc.body || !doc.body.contains(button)) return false;
    const win = doc.defaultView;
    for (let n = button; n && n !== doc.body; n = n.parentElement) {
      if (n.hidden || (win && win.getComputedStyle(n).display === "none")) return false;
    }
    return true;
  }

  // The stream shows its latest posts and loads older ones as its document is scrolled to the bottom
  // (spec 006 research S17: 61 → 92 → 105 posts on one class, 2026-11-24; #293).
  const postCount = (doc) => doc.querySelectorAll("[data-stream-item-id]").length;
  function scrollToEnd(doc) {
    const win = doc.defaultView;
    try { win.scrollTo(0, doc.documentElement.scrollHeight); } catch (_) { /* a frame with no layout */ }
    for (const el of doc.querySelectorAll("*")) {
      if (el.scrollHeight > el.clientHeight + 20 && /(auto|scroll)/.test(win.getComputedStyle(el).overflowY)) el.scrollTop = el.scrollHeight;
    }
  }

  // The first «Ver más publicaciones» button a page shows, if any.
  function shownMore(doc) {
    return [...doc.querySelectorAll(MORE_BUTTON)].find(isShown) || null;
  }

  // The default loader: a hidden same-origin iframe, so the injected script is never lost. It polls
  // from the start; a frame that leaves Classroom (Google's sign-in) is an expired session. It waits
  // while the tab is hidden, and time spent hidden counts towards nothing. A ready page is taken once
  // its reading has held still for `settleMs` on screen, unbroken since the tab was last shown; one
  // that keeps changing for `settleCapMs` is `unsettled`, a failed load like a timeout (loaded again,
  // then what any failed load leads to: an item page or the stream left out, the capture incomplete;
  // a «Trabajo de clase» stops its class). A «Trabajo de clase» that has held still and shows «Ver
  // más publicaciones» is not taken: the button is pressed and the page waited for until its reading
  // changes — only that: a button hidden with no new row is no answer — then it settles again, until
  // no topic shows the button (#288). A press the page does not answer within `moreTimeoutMs`
  // (`more_unanswered`), or a button still shown after
  // `maxPresses` of them (`more_endless`), is a failed load: a list still cut is never read whole.
  // The stream, once it holds still, is scrolled to its bottom and waited for: older posts that come
  // within `streamWaitMs` settle and it is scrolled again; none coming is its end (#293). More than
  // `maxScrolls` is a failed load (`stream_endless`): the stream left out, the capture incomplete.
  function iframeLoader(win, { timeoutMs = 40000, attempts = 2, settleMs = 1500, settleCapMs = 10000, pollMs = 300, moreTimeoutMs = 20000, maxPresses = 30, streamWaitMs = 6000, maxScrolls = 100 } = {}) {
    const classwork = (path) => /\/w\/[^/]+\/t\/all$/.test(path);
    const stream = (path) => /^\/u\/\d+\/c\/[^/]+$/.test(path);
    const once = (path) => new Promise((resolve, reject) => {
      const frame = win.document.createElement("iframe");
      frame.style.cssText = "position:absolute;left:-10000px;width:1200px;height:800px;visibility:hidden";
      frame.src = path;
      win.document.body.appendChild(frame);
      let started = Date.now();
      let tick = Date.now();
      let wasHidden = false; // the step back on screen counts nothing: the gap was spent hidden
      let ready = false;
      let reading = null; // what the ready page showed at the last poll
      let still = 0; // time on screen the reading has not changed
      let settling = 0; // time on screen since the page was first ready
      let presses = 0; // «Ver más publicaciones» pressed on this page
      let waiting = false; // a button was pressed and its rows have not come yet
      let pressed = null; // the reading when it was pressed
      let answering = 0; // time on screen since that press
      let scrolls = 0; // the stream scrolled to its bottom on this page
      let scrolledFrom = null; // the posts it had then, until more come or none do within streamWaitMs
      let scrollWait = 0; // time on screen since that scroll
      let streamEnded = false; // a scroll brought nothing: the stream is read whole
      const stop = (err) => { win.clearInterval(poll); frame.remove(); reject(err); };
      const poll = win.setInterval(() => {
        const now = Date.now();
        if (win.document.visibilityState === "hidden") { started = now; tick = now; wasHidden = true; return; }
        const step = wasHidden ? 0 : now - tick;
        if (wasHidden) { started = now; still = 0; } // back on screen: a held-back paint may come now
        tick = now;
        wasHidden = false;
        let doc = null;
        try { doc = frame.contentDocument; } catch (_) { doc = null; }
        if (doc === null || (doc.location && /accounts\.google\.com/.test(doc.location.host))) {
          stop(new SessionExpired()); return;
        }
        if (doc.body && doc.location.href !== "about:blank" && pageReady(path, doc)) {
          const current = pageReading(path, doc);
          if (waiting) {
            // Only a change in what the page reads is an answer: a button hidden or drawn again
            // while its rows are on their way is not, or the old rows would be taken for the whole.
            if (current === pressed || current === null) {
              answering += step;
              if (answering >= moreTimeoutMs) stop(new Error("more_unanswered"));
              return;
            }
            waiting = false; reading = current; still = 0; settling = 0; started = now; // answered: settle again
            return;
          }
          if (scrolledFrom !== null) {
            if (postCount(doc) > scrolledFrom) {
              scrolledFrom = null; reading = current; still = 0; settling = 0; started = now; // older posts came
              return;
            }
            scrollWait += step;
            if (scrollWait < streamWaitMs) return;
            scrolledFrom = null; streamEnded = true; // nothing came: the stream's end
          }
          if (!ready) {
            ready = true; reading = current; still = 0;
          } else {
            settling += step;
            if (current === reading) { still += step; } else { reading = current; still = 0; }
          }
          const more = still >= settleMs && classwork(path) ? shownMore(doc) : null;
          if (still >= settleMs && stream(path) && !streamEnded) {
            if (scrolls >= maxScrolls) { stop(new Error("stream_endless")); return; }
            scrolls += 1; scrolledFrom = postCount(doc); scrollWait = 0; started = now;
            scrollToEnd(doc);
          } else if (more) {
            if (presses >= maxPresses) { stop(new Error("more_endless")); return; }
            presses += 1; waiting = true; pressed = current; answering = 0; started = now;
            more.click();
          } else if (still >= settleMs) {
            win.clearInterval(poll);
            resolve({ doc, path: frame.contentWindow.location.pathname });
            win.setTimeout(() => frame.remove(), 0);
          } else if (settling >= settleCapMs) {
            stop(new Error("unsettled"));
          }
        } else {
          ready = false; // it was ready and is not any more: its reading starts again when it is
          if (now - started > timeoutMs) stop(new Error("timeout"));
        }
      }, pollMs);
    });
    return async (path) => {
      let last;
      for (let i = 0; i < attempts; i++) {
        await whileHidden(win);
        try { return await once(path); } catch (err) { if (err && err.name === "SessionExpired") throw err; last = err; }
      }
      throw last;
    };
  }

  function fileName(capture) {
    const owner = capture.type === "class" ? capture.class.id : capture.type === "stop" ? capture.class || "stop" : "classes";
    return `alfabeta-capture-${capture.run}-${owner}-${stamp(new Date(capture.captured_at))}.json`;
  }

  // Leaves the capture in the downloads folder, as the skill collects it (research R12).
  function save(capture, win) {
    const blob = new win.Blob([JSON.stringify(capture)], { type: "application/json" });
    const link = win.document.createElement("a");
    link.href = win.URL.createObjectURL(blob);
    link.download = fileName(capture);
    link.dispatchEvent(new win.MouseEvent("click"));
    return link.download;
  }

  root.alfabetaExtract = {
    VERSION, MIN_WAIT_MS, detectStop, readClasses, readClasswork, readDetail, readStream, attachmentOf,
    captureClasses, captureClass, iframeLoader, pageReady, shownMore, MORE_BUTTON, SessionExpired, fileName, save, base64,
  };
})(typeof globalThis !== "undefined" ? globalThis : this);
