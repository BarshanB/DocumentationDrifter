# 18: Serve the console from the v1 app

**What to build:** A person who opens the service's root URL gets the console (`Source/Frontend/index.html`) and can run an analysis and look up a run against the same app, before v1.2 starts. `GET /` returns the page unchanged, outside `/system`, so the contract, the OpenAPI document and conformance stay as they are. The page keeps its repo watching, its API address field and `?demo`, and `ui.py` stays as the way to run the console against an API elsewhere.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human · built locally (2026-10-18), open until the Railway check. `GET /` serves the page through a `FileResponse`, outside the OpenAPI document; three tests in `tests/test_v1_console.py`, and the suite is green offline (215 passed, 34 skipped). Locally the console analysed the test repo's `main` tip (05128cd → 3aa60e6) and showed `manifest.json` ADDED, OTHER, nothing skipped, no issues: the same answer the reference service gave for that pair. That pair is the one the page's watch flow produces; no manifest label covers it, so the reference was the source of truth. The `modified` label matched the manifest through `/system/analyze` on the same app. Decided on 2026-10-18 (grilling Q1 to Q12).

**Spec:** docs/plan/roadmap.md, "A basic UI is in v1"; docs/plan/decisions.md, the 2026-10-18 entry

- [x] `GET /` answers 200 with `text/html` and the bytes of `Source/Frontend/index.html`.
- [x] `GET /` is left out of `/system/openapi.json`, and every `/system` route answers as before.
- [x] `POST /system/analyze` answers from the same app the page is served by.
- [x] Locally, `uvicorn` plus `localhost:8000/` analyzes the ticket 11 test repo, and the console shows its expected answers.
- [ ] On Railway, the same check passes against the deployed URL (only after Kaan says push).
- [x] The decision log has a dated entry for "a basic UI is in v1, served at `/`"; the roadmap paragraph, the Frontend README and the "only /system" comments in `api.py` and the Dockerfile say the console is served at `/`.
- [x] `to_do.md` notes, under "left for a complete solution", that each viewer polls GitHub on their own 60-an-hour unauthenticated budget.
- [x] The whole suite is green offline.
