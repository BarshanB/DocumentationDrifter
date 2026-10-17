# DocumentationDrifter
A program to detect documentation drift in a GitHub repo. Designed for ECE30861 Class Project. 

First Deliverable stage functions essentially as an LLM wrapper that tracks GitHub changes. Very rudimentary, perhaps we can begin to work on our mapping scheme.
## v1.1 change detection API

`POST /system/analyze` takes `{"repository": "owner/name", "commit_id": "<7-40 hex>", "base_commit": "<optional>"}` and returns every changed file of a public GitHub repo with its change type and category. `GET /system/analysis/{analysis_id}` returns the saved run byte for byte. The contract matches the reference service; see `plan/spec-v1.1.md`.

**Run locally**

```bash
pip install -r requirements.txt
uvicorn --app-dir Source GitHub_Connector.api:app --port 8000
python -m pytest -q            # DRIFTER_OFFLINE=1 skips the GitHub tests
```

**Container:** `docker build -t drifter .` then `docker run -p 8000:8000 drifter`. The image has git, no credentials, and serves only the v1 app.

**Settings** (environment, all optional): `DRIFTER_REMOTE_BASE_URL`, `DRIFTER_RUNS_DIR`, `DRIFTER_CLONE_DIR`, `DRIFTER_RULES_FILE`, `DRIFTER_GIT_TIMEOUT` (60 s), `DRIFTER_ANALYSIS_DEADLINE` (120 s), `DRIFTER_MAX_CONCURRENT` (2), `DRIFTER_MAX_FILE_BYTES` (1 MB).

**Public URL:** not deployed yet. `render.yaml` holds the Render free-tier setup, applied once Kaan approves it.

**Free tier, read before reporting a bug.** Call `GET /system/health` first: Render spins the service down after 15 idle minutes and it takes about a minute to wake. Run files live on local disk, which is wiped on spin-down, restart and redeploy, so a `GET` for an old run can return 404 on both teams' services. That is expected until v3 adds durable storage.
