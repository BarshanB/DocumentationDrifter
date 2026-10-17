# DocumentationDrifter
A program to detect documentation drift in a GitHub repo. Designed for ECE30861 Class Project. 

First Deliverable stage functions essentially as an LLM wrapper that tracks GitHub changes. Very rudimentary, perhaps we can begin to work on our mapping scheme.
## v1.1 change detection API

`POST /system/analyze` takes `{"repository": "owner/name", "commit_id": "<7-40 hex>", "base_commit": "<optional>"}` and returns every changed file of a public GitHub repo with its change type and category. `GET /system/analysis/{analysis_id}` returns the saved run byte for byte. The contract matches the reference service; see `plan/spec-v1.1.md`.

**Route list.** Opening plain `/system` returns the list of routes. The reference service has no such route; it stays out of the OpenAPI document.

**Course test routes.** `POST /system/test/setup` with `{"session_id": "...", "setup": {...}}` opens a session (201, or 409 if the id is taken). `GET /system/test/report?session_id=...` then reports how many executable lines of the v1 code ran while handling requests since that setup: `{"session_id", "coverage": {"code": {"covered", "total", "basis"}}}`. Both match the reference service's shapes and error bodies (`{"message", "source": "system"}`). Sessions live in memory, so a restart or redeploy forgets them and their report becomes 404.

**Test repo.** The labelled test cases live in a public repo, [kaan-kanadasi/DocumentationDrifter-testrepo](https://github.com/kaan-kanadasi/DocumentationDrifter-testrepo), built by `tools/testrepo.py`. The online label tests use it by default (`DRIFTER_TEST_REPO=owner/name` points them elsewhere, an empty value turns them off). After changing any label, republish it from an account that can push there: `python tools/testrepo.py /tmp/testrepo` then `git -C /tmp/testrepo push --force https://github.com/kaan-kanadasi/DocumentationDrifter-testrepo main`. The `label/*` tags are optional; the tests find labels by the SHAs in the manifest. `DRIFTER_LABEL_CONFORMANCE=1` also compares every label with the reference service; it stays off until the ticket 12 differences are settled.

**Run locally**

```bash
pip install -r requirements.txt
uvicorn --app-dir Source GitHub_Connector.api:app --port 8000
python -m pytest -q            # DRIFTER_OFFLINE=1 skips the GitHub tests
```

**Container:** `docker build -t drifter .` then `docker run -p 8000:8000 drifter`. The image has git, no credentials, and serves only the v1 app.

**Settings** (environment, all optional): `DRIFTER_REMOTE_BASE_URL`, `DRIFTER_RUNS_DIR`, `DRIFTER_CLONE_DIR`, `DRIFTER_RULES_FILE`, `DRIFTER_GIT_TIMEOUT` (60 s), `DRIFTER_ANALYSIS_DEADLINE` (120 s), `DRIFTER_MAX_CONCURRENT` (2), `DRIFTER_MAX_FILE_BYTES` (1 MB).

**Public URL:** being set up on Railway's free plan (`railway.toml`: Dockerfile build, `/system/health` health check).

**Free tier, read before reporting a bug.** Call `GET /system/health` first: the free service sleeps after about 5 to 10 minutes without traffic, and the first request after that can take a moment or answer 502. Run files live on local disk, which is wiped on every redeploy and restart, so a `GET` for an old run can return 404 on both teams' services. That is expected until v3 adds durable storage.
