"""Local check of the probe's parsing and of reading answers inside a sync response handler."""
import json, sys, types
sys.modules["read"] = types.ModuleType("read")
sys.path.insert(0, ".")
import s8_calls as S
payload = json.dumps([["hrq.crs", [["123456", "x"]]], "colegio.es"])
body = ")]}'\n\n123\n" + json.dumps([["wrb.fr", "abcD1", payload, None, None, None, "generic"], ["di", 42]]) + "\n25\n" + json.dumps([["e", 4, None, None, 99]])
rows = S.answer_rows(body)
print(rows[0][0], S.tags_of(rows[0][1]))
assert rows[0][0] == "abcD1" and S.tags_of(rows[0][1]) == ["hrq.crs"]
assert S.masked("/u/3/c/c3ludGgtMQxx/a/c3l1/details") == "/u/N/c/ID/a/ID/details"; assert S.masked("/a/colegio.es/x@y") == "/a/ID/ID"
assert S.b64decode("c3ludGgtMQ") == "synth-1"
from playwright.sync_api import sync_playwright
got = []
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.route("**/*", lambda r: r.fulfill(body=body if "batchexecute" in r.request.url else "<html><body>x</body></html>", content_type="text/html"))
    pg.on("response", lambda r: got.append(r.text()[:4]) if "batchexecute" in r.url else None)
    pg.goto("http://example.test/u/0/h")
    pg.evaluate("fetch('/_/ClassroomUi/data/batchexecute?rpcids=abcD1', {method:'POST'}).then(r=>r.text())")
    pg.wait_for_timeout(500); b.close()
print("handler read:", got); assert got == [")]}'"]
