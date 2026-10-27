# Fixtures for `alfabeta.notes` (spec 005)

Every file here is a recorded response with invented values, named `<call>-<YYYY-MM-DD>.json`:
the Drive or Claude call it answers, and the date it was captured. Personal values (names, addresses,
Drive ids, tokens) are replaced before a file is added.

Images are drawn by the tests themselves. No photo of real class notes is ever stored here.

`changes-*.json` are `changes.list` pages in Drive v3's documented shape (fields of spec 005
research R2), written by hand with invented ids and names. None is captured from a real call yet;
the live check is spec 005's quickstart (research R8 of spec 004 asks for captures).

`claude-*.json` are Messages API answers in the documented shape (Claude API errors page and
response reference, read 2026-10-27), with invented text and ids; none is captured. The spend-limit
message is not documented at all, only its status and type: quickstart step 3 records the real one.
