// The Node half of the gate runs: jsdom loads and parses a page.
import { test } from "node:test";
import assert from "node:assert/strict";
import { JSDOM } from "jsdom";

test("jsdom parses a page", () => {
  const dom = new JSDOM("<main><h1>Trabajo de clase</h1></main>");
  assert.equal(dom.window.document.querySelector("h1").textContent, "Trabajo de clase");
});
