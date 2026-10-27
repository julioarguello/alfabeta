# Classroom fixtures

Everything here is synthetic or invented. No page of a real student enters the repository
(constitution III and IV, spec 001 research R8).

## `pages/`: synthetic pages for the extractor's tests

| File | Source page type | How it was made |
|---|---|---|
| `home.html` | Home (`/u/<n>/h`) | `anonymize` over the page saved by spike S3 on 2026-10-25 |
| `classwork.html` | «Trabajo de clase» (`/u/<n>/w/<class>/t/all`) | same |
| `assignment-detail.html` | Assignment detail (`/u/<n>/c/<class>/a/<item>/details`) | same |
| `material-detail.html` | Material detail (`/u/<n>/c/<class>/m/<item>/details`) | same |
| `question-detail.html` | Question detail (`/u/<n>/c/<class>/mc/<item>/details`) | same |
| `stream.html` | Stream (`/u/<n>/c/<class>`) | same |
| `challenge.html` | Anti-bot challenge | written by hand |
| `classwork-other-language.html` | «Trabajo de clase» with English labels | written by hand |

The anonymised pages were generated on 2026-10-27. They keep tags, CSS classes, hierarchy, the
label allowlist of research R8 and the short enumerations the page uses for structure
(`data-stream-item-type`, `data-visibility`, `aria-*`); texts, ids and dates are invented, and
scripts and stylesheets are emptied. Ids become `synth-<n>` in the same position of each URL.

Measured 2026-10-27 against the six pages saved by S3: the number of elements matching each of
these selectors is the same in the original and in its synthetic page: `[data-stream-item-id]`,
`[data-stream-item-type]`, `[data-topic-id]`, `a[href*="/details"]`, `a[href*="/mc/"]`,
`a[href*="/w/"]`, `a[href*="docs.google.com"]`, `a[href*="drive.google.com"]`, `[aria-label]`,
`li`. None of the 114 item and topic titles of the 2026-10-26 capture appears in a synthetic page.

To regenerate one, from the real page saved outside the repository:

```bash
uv run --locked python -m alfabeta anonymize ~/.alfabeta/<student>/data/raw-captures/<page>.html tests/fixtures/classroom/pages/<page>.html
```

## `*.json`: invented captures

Captures shaped as the extractor would write them (`contracts/capture.schema.json`), with the
invented run `run-sintetico`, which `sandbox download --captures` replaces (spec 001 T029).
