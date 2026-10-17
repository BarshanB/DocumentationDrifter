# 01: Tracer: one commit analysed, saved and served back, and a missing repository refused

**What to build:** A caller posts a repository and a head commit (as a full SHA) for a local fixture repo and gets 200 with a complete AnalysisResult. It lists the head's added, modified and deleted files against its first parent, each categorised OTHER by a rules file that holds only the fallback rule for now, and GET /system/analysis/{id} returns the same bytes from the run store. A repository with nothing behind the remote base URL fails with 404 REPOSITORY_NOT_FOUND in an ErrorBody and saves nothing; this lays down the one error path every later failure reuses, while the connector really clones anonymously, blobless and without checkout, and deletes the clone when its scope exits.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Spec:** plan/spec-v1.1.md, user stories 1, 2, 3, 4, 5, 6, 7, 9, 14, 18, 22, 31, 34, 35, 37, 38, 43, 44, 45, 46, 47, 48, 52

- [ ] A shared test fixture builds a bare fixture repo in its own folder under the test's temporary directory, away from v0's test database. It sets its own git identity so it runs on a clean machine, and it is not named client. It accepts partial clones and fetches by SHA the way GitHub does, so the blobless path is really exercised and doesn't quietly fall back to a full clone.
- [ ] The remote base URL is a config value that defaults to GitHub. Each test repoints it, along with the run store location and the temporary-clone location, using the settings pattern v0's tests already use. v0's own settings and tests are left as they are.
- [ ] The v1 app is its own FastAPI app. Every route is on the /system router. Its OpenAPI document is served at /system/openapi.json and lists no v0 webhook route. It has no lifespan, and its handlers are plain functions that only call analyze(). Importing it never imports v0's webhook app.
- [ ] The API models for AnalysisRequest, AnalysisResult, Change, Finding, Skipped and ErrorBody copy the reference service's schemas field for field. The only change is DOCUMENTATION added to the category enum used by Change and Finding. ticket 09 checks these models against the reference service.
- [ ] POST /system/analyze with a repository and a full-SHA head commit returns 200 with all twelve AnalysisResult fields: analysis_id is an- plus 32 hex characters; head_commit is the full SHA; base_commit is the head's first parent; config_version is a string; tool_version names the build; status is SUCCESS; error is null; issues[] and skipped[] are empty; and created_at is ISO 8601 UTC with milliseconds and a Z.
- [ ] A head commit that modifies one file gives exactly one MODIFIED change, with old_path null and category OTHER. The file is one that only the fallback rule matches, so this still holds once the full path rules land. A head commit that adds one file and deletes another gives one ADDED change and one DELETED change, and changes[] is sorted by path.
- [ ] A base_commit given as a full SHA that is already in the clone is used as the base commit. Every other base case arrives with ticket 04, so a given base is never silently ignored.
- [ ] The path rules live in one rules file, which for now holds only the fallback rule, and config_version is a short hash of that file.
- [ ] GET /system/analysis/{id} returns a body byte-identical to the POST body (AC-06, T-05). The run store offers save, load and dump, and dump is the only serializer. Each run file is written once, and git ignores the run store's folder.
- [ ] Three identical requests give results that differ only in analysis_id and created_at.
- [ ] An owner/name with no fixture repo behind the remote base URL returns 404 with an ErrorBody. Its code is REPOSITORY_NOT_FOUND and its message follows the reference service's wording ('not found or is not public'). analyze() raises an analysis error that carries a code and a message, the route turns it into a status through one table that covers all five contract codes, and no run file is saved.
- [ ] The connector is the only code that runs git. It runs git anonymously, with terminal prompts off and an empty credential helper, and makes a blobless, no-checkout clone into a fresh temporary directory. It is used as a scope that deletes the clone on exit, so the temporary-clone location is empty after a SUCCESS and after a REPOSITORY_NOT_FOUND. The connector uses dataclasses inside, and Pydantic is used only for the API models.
- [ ] The fixture repo is byte-identical before and after an analysis (AC-09). A fixture repo that holds files which would leave a marker if they were installed, imported or run leaves no marker.
- [ ] GET /system/health returns 200 with the reference service's body (a status, plus storage reported as local) and does no git work.
- [ ] One test calls analyze() directly, without the HTTP client, and gets the same result apart from analysis_id and created_at.
- [ ] The whole suite is green, v0 included: 18 tests pass and 1 skips without the local environment file.
