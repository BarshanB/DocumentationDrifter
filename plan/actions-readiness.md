# GitHub_Connector, Phase 3 scope and GitHub Actions readiness

Written 2026-10-17 against `main` @ `76eb691`, the v1 models in [Models/v1](../Models/v1/README.md) and the [roadmap](roadmap.md). It answers three questions from Kaan: is `Source/GitHub_Connector/` aligned with what the Phase 3 docs and pictures say, how can the architecture pair with GitHub Actions later without building it now, and do the v1 pictures make scaling easier after Phase 3. Every finding below was checked twice: once by the reviewer who found it and once by a second reviewer who tried to refute it. Where the second reviewer corrected a claim, the corrected version is the one written here. Line numbers and quotes from the roadmap and guide in sections 1 to 3 describe those files before the 2026-10-17 edits listed under "Edits applied".

## Short answers

1. **The directory is aligned but outside Phase 3.** `Source/GitHub_Connector/` holds only the v0 webhook receiver, which matches the roadmap's "v0 (done)" table and M1's dashed "Webhook receiver" box. It is harmless while nothing serves it. It only becomes a problem if v1 is built on top of it (see "Collisions to avoid").
2. **Pairing with Actions needs two small seams in v1, not new features.** The first is an `analyze()` function that the HTTP route only wraps. The second is a run store behind `save(id, bytes)` and `load(id)`. Everything else waits for v3. The one Phase 3 piece worth adding is a workflow that runs the acceptance and conformance tests against the deployed URL, which the spec already asks for (§8.1).
3. **The pictures are ready for new features after small edits, but not yet for load.** Feature growth (v2 findings, the v3 Action, reviews) fits with four small diagram edits. Load growth (more repos, saved runs that last) is blocked by local-disk storage on Render's free tier. That limitation is fine for the Phase 3 demo, but it is the first thing v3 must change. Two outright errors in M4 and M5 are already fixed (see the end).

## 1. GitHub_Connector against the Phase 3 docs

| What | Verdict | Evidence |
|---|---|---|
| Webhook receiver: HMAC over raw bytes, `ping`, dedupe on `X-GitHub-Delivery`, `before`/`after` stored in SQLite, `GET /health` | Matches the roadmap's v0 table and M1's dashed box | `gitHook.py:30-100`, `store.py:38-63`, `roadmap.md:63-64`, `M1-context.md:32` |
| Zero SHA becomes `None` (`parse.py`) | Matches guide step 3, but see the first-audit gap below | `parse.py:9-10,45-49`, `github-connector-steps.md:68` |
| SQLAlchemy, pydantic-settings, `.env`, `WEBHOOK_SECRET` | v3 material. Dormant and harmless in v1 | `config.py:12-20`, `requirements.txt:3-5` |
| Tests | 19 collected, **18 pass and 1 skips**. The skipped test needs a `.env`, which is gitignored, so it also skips in CI | `tests/test_config.py:48-53`, `.gitignore:2` |
| Untested v0 paths | `GET /health`, the 500 when the secret is unset, and the 400 when the delivery id is missing have no test | `gitHook.py:44-47,62-72` |

### Collisions to avoid when v1 lands next to it

The roadmap says v1 lives "in `Source/GitHub_Connector/` next to the v0 webhook code" (`roadmap.md:76`). That works if v1 keeps these apart:

- **One deployable app, and it is not `gitHook.app`.** `gitHook.app` has a lifespan that creates `drifter.db` at startup, a root `/health` and `/openapi.json`, and a public `/hooks/github`. Slice 1 checks `/system/openapi.json` against the pod's. So v1 needs its own `FastAPI(openapi_url="/system/openapi.json")` app in a new module, with no lifespan and all routes on `APIRouter(prefix="/system")`, and the Dockerfile serves only that app. Including `gitHook.app.router` later would also pull in its lifespan and second docs pages (checked at runtime), so in v4, when the webhook is wired (roadmap decision 14), the receiver gets its own router first.
- **Different module names.** `models.py`, `store.py`, `parse.py` and `config.py` are the obvious names for v1's API models, run store, diff parser and rules file, but each already means the v0 thing. Suggested v1 names: `api.py`, `analysis.py`, `fetch.py`, `rules.py` plus its rules file, `runs.py` and `schemas.py`.
- **Two meanings of "GitHub connector".** In M1 the connector is the outbound git fetcher inside the v1 boundary. The folder of the same name holds the inbound webhook, which M1 draws outside it. One line in `Models/v1/README.md` that maps each M1 box to its file fixes this without renaming anything.
- **Plain `def` handlers.** `receive()` is `async def` and calls synchronous code (`gitHook.py:51,87`). If v1 copies that with `subprocess.run`, every git call blocks the event loop and requests run one at a time, `/system/health` included. v1 handlers should be plain `def`, so FastAPI runs them in its thread pool.
- **Tests.** The autouse fixture in `tests/conftest.py:18-33` writes `test.db` into `tmp_path` for every test. v1's fixture repos must live in `tmp_path / "repo"`, or `git add -A` commits that file and breaks exact `changes[]` assertions. The `client` fixture name is also taken.
- **`.gitignore`** has no `runs/` entry, so local run files from slice 9 would show up in `git status`.

### Stale statements in the docs

- `roadmap.md:65,129` say "19 tests" and "all 19 still pass". The run shows 18 pass and 1 skips without a `.env`.
- `commit-fetcher-plan.md:5-11` still describes the stubs from `5b74560` (`monitor()`, `get_diff()`). None of them exist now, and its error row still says `REPO_NOT_FOUND`.
- `roadmap.md:190` points at "the original outline in store.py", which was replaced in `e3a718e`.
- `README.md:4` calls the tool "an LLM wrapper". That is no longer stale: Kaan decided (2026-10-17, roadmap decision 4) that v1.1 is the git-only connector and v1.2 adds an LLM whose output may be probabilistic, overriding spec §8.2; deterministic output is a goal only for the final version. `Source/LLM_Shell/` is Muhammad's newest commit, so ask him whether it is the start of that v1.2 work before touching it.
- `documentation-drifter-plan.md:71` sets head = `github.sha`. On a `pull_request` event that is GitHub's synthetic merge commit, not the PR head.

## 2. How to pair with GitHub Actions

### What the Action should be

The spec already chooses this: "Our team will build workflows to call the web service" (the end product, §8.1). So the v3 Action is a **thin HTTP client of `POST /system/analyze`**. It works out head and base from the event, sends a normal `AnalysisRequest`, and reports the result. The shared contract does not change, the run is saved where `GET /system/analysis/{id}` and the v3 review loop can find it, and conformance with the pod holds by construction.

There is a second mode for later: run our code inside the runner against the repo's own checkout. That scales better (each repo's runner pays), has no cold start and can read private repos. But its runs never reach our service, so they can't be reviewed or listed. Keep it as a v4 option. The `analyze()` seam below makes it cheap to add then.

### Seams to build in v1 (they cost almost nothing now)

| Seam | Where | Why it matters later |
|---|---|---|
| `analyze(repository, commit_id, base_commit=None) -> AnalysisResult`, raising `AnalysisError(code, message)` | Slice 1. Route handlers call it and do no git or file work themselves. A `RequestValidationError` handler still maps FastAPI's 422 to 400 `INVALID_REQUEST` | The v3 Action (through the route), the v4 webhook worker, a v4 CLI and the tests all reach the same function. M2's final states become the error codes |
| Run store as `save(id, bytes)` and `load(id)` plus one `dump(result)` serializer | Slice 9 | v3 swaps local disk for a durable store by changing one module. One serializer keeps `GET` byte-identical (AC-06) |
| A `with fetch(repo, head, base) as cmp:` scope that deletes the clone on exit | Slices 3–7 | v2 detection reads the mapping file at base and head inside the same scope, instead of re-cloning |

Build nothing else for Actions in v1. Checkout mode, a CLI and `pyproject.toml` are flagged as missing, not built, per `Skills/CLAUDE.md`.

### The one Actions piece that is in Phase 3 scope

Spec §8.1 also says Actions "run automated acceptance tests". Slice 12 covers only `pytest` on PRs, and the slice 10 conformance test is skipped offline. Adding a second workflow, `acceptance.yml`, closes that:

- Trigger it with `workflow_dispatch`, plus an optional schedule.
- Warm the service with retries on `GET /system/health`.
- Run T-01 to T-07 and the conformance test against the deployed URL.

It exercises exactly what the v3 Action needs (cold-start handling, long timeouts, head and base inputs). The v3 Action then starts as a copy of a job that already works.

### v3 Action design, decided now so v1 doesn't paint us in

**Head and base per event.** Always send a real base. That covers every case through the existing contract:

| Event | Head | Base |
|---|---|---|
| `pull_request` (opened, synchronize, reopened) | `pull_request.head.sha`, never `github.sha` | merge base of `pull_request.base.sha` and head |
| `push`, normal | `after` | `before` |
| `push`, force push | `after` | merge base of `before` and `after` |
| `push`, new branch (`before` is 40 zeros) | `after` | merge base of the default branch and `after` |
| `push`, branch deleted (`after` is 40 zeros) | skip | skip |

All the merge bases come from one call to GitHub's compare endpoint, `GET /repos/{owner}/{repo}/compare/{base}...{head}`, which returns `merge_base_commit` with the default read token. So the Action needs no `actions/checkout` and no full-history clone.

**Why the new-branch row matters.** (Decided as roadmap decision 15; the graphs and the final reasoning are in [new-branch-base.md](new-branch-base.md).) The guide (`github-connector-steps.md:68`) and roadmap v3 item 2 (`roadmap.md:168`) say a zero `before` means a first audit. But our contract can't ask for one: leaving out `base_commit` means "first parent", and 40 zeros as `base_commit` would get 404 `COMMIT_NOT_FOUND`. Sending the merge base with the default branch avoids both, and avoids listing the whole repo as ADDED on every new branch. "First audit" then means a root commit only. Those two lines and the comment at `parse.py:41` should say so.

**Workflow rules.**

- **Triggers:** `push` on the default branch, plus `pull_request`. Without the branch filter, a push to a PR branch is analysed twice.
- **Never `pull_request_target`.** It hands fork code the base repo's write token and secrets.
- **Permissions:** `contents: read` only. Add `pull-requests: write` in a separate job for comments.
- **Fork PRs:** the token is read-only there, so report through `$GITHUB_STEP_SUMMARY` and leave comments to same-repo PRs.
- **Retries:** call `GET /system/health` first, with retries. Then send one `POST /system/analyze` with a long timeout and no retry. A retried POST repeats the most expensive request and creates extra `analysis_id`s.
- **Concurrency:** a concurrency group cancels pending runs even without `cancel-in-progress`. Use a unique group per push run (`github.run_id`), and cancel only superseded PR runs.
- **Run file:** upload it as a workflow artifact. Artifacts expire after at most 90 days, so this is a convenience copy, not the REQ-04 evidence.
- **Distribution:** if our repo stays private, public repos can't `uses:` an action or reusable workflow from it. Ship a copy-paste workflow template, or publish the action from a public repo.

A sketch of that workflow, for later and not built now:

```yaml
on:
  push: {branches: [main]}
  pull_request:
permissions: {contents: read}
concurrency:
  group: drift-${{ github.event.pull_request.number || github.run_id }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
jobs:
  drift:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    env: {URL: "https://<our-service>.onrender.com/system"}
    steps:
      - id: pair   # head and base per the table above, merge base from the compare API
        env:
          GH_TOKEN: ${{ github.token }}
          EVENT: ${{ github.event_name }}
          BEFORE: ${{ github.event.before }}
          AFTER: ${{ github.event.after }}
          PR_BASE: ${{ github.event.pull_request.base.sha }}
          PR_HEAD: ${{ github.event.pull_request.head.sha }}
          DEFAULT: ${{ github.event.repository.default_branch }}
        run: |
          zero=0000000000000000000000000000000000000000
          if [ "$EVENT" = pull_request ]; then head=$PR_HEAD; from=$PR_BASE
          elif [ "$AFTER" = "$zero" ]; then echo "skip=true" >> "$GITHUB_OUTPUT"; exit 0
          elif [ "$BEFORE" = "$zero" ]; then head=$AFTER; from=$DEFAULT
          else head=$AFTER; from=$BEFORE; fi
          base=$(gh api "repos/$GITHUB_REPOSITORY/compare/$from...$head" --jq .merge_base_commit.sha)
          if [ "$base" = "$head" ]; then echo "skip=true" >> "$GITHUB_OUTPUT"; exit 0; fi   # new default branch: nothing to compare
          echo "head=$head" >> "$GITHUB_OUTPUT"; echo "base=$base" >> "$GITHUB_OUTPUT"
      - if: steps.pair.outputs.skip != 'true'
        env: {HEAD: "${{ steps.pair.outputs.head }}", BASE: "${{ steps.pair.outputs.base }}"}
        run: |
          curl -fsS --retry 6 --retry-all-errors --max-time 90 "$URL/health" > /dev/null
          jq -n --arg r "$GITHUB_REPOSITORY" --arg h "$HEAD" --arg b "$BASE" \
            '{repository: $r, commit_id: $h, base_commit: $b}' |
          curl -sS --max-time 150 -H 'Content-Type: application/json' -d @- \
            -o run.json -w '%{http_code}\n' "$URL/analyze" | tee code.txt
          jq -r '"### DocumentationDrifter\n\(.analysis_id // .code): \(.changes // [] | length) changes, \(.issues // [] | length) findings"' \
            run.json >> "$GITHUB_STEP_SUMMARY"
          grep -q '^200$' code.txt
      - if: always() && steps.pair.outputs.skip != 'true'
        uses: actions/upload-artifact@v4   # pin the current major when this is built
        with: {name: "drifter-run-${{ github.run_id }}", path: run.json, if-no-files-found: ignore}
```

### Make the Action the only v3 trigger

Roadmap v3 plans both the Action and the wired webhook on `push` (`roadmap.md:168,170`), so every push would be analysed twice. The webhook also can't work reliably on Render's free tier. A sleeping service takes about a minute to start, GitHub gives a webhook 10 seconds, and GitHub does not redeliver failed deliveries on its own. So the first push after 15 idle minutes is lost. The Action can wait out a cold start. Recommendation: the Action is the v3 trigger, and the webhook stays dormant until the v4 GitHub App. Nothing in v0 is thrown away.

## 3. Do the pictures make scaling easier after Phase 3?

All the changes in this table were applied on 2026-10-17 (see "Edits applied" below).

| Model | Verdict | What already helps | Smallest change |
|---|---|---|---|
| M1 context | Ready with changes | Clear boundary, anonymous clone, one write path, later callers drawn dashed | Note that routes call `analyze()`, and that the webhook and Action reach it as callers. Label the run store "save / load by id, local disk in v1". Point the dashed reviewer arrow at a separate dashed "Review records · v3" box, because run files are write-once. |
| M2 lifecycle | Ready with changes | Closed set of final states, nothing saved on failure, one temporary clone per request | One line: these are the states of `analyze()`, and HTTP maps each final state to a code. Add two guards: an overall deadline (ends in 500 `TIMEOUT`) and a limit on concurrent analyses. Keep it synchronous: a QUEUED state would break the pod contract. |
| M3 file rules | Ready with changes | Rules in one hashed config file, first match wins | Define `config_version` as a hash of every config input: the rules file in v1, plus the mapping file from v2. Say which side the binary and UTF-8 checks read (head, or base for DELETED). |
| M4 run file | Ready with changes | Contract copied, write-once files, full SHAs, ERROR status already in the enum | **Fixed now:** `Finding` was missing `change_category` and `explanation`. Also done: `finding_id` must be deterministic (a hash of issue type, code file and doc file), or AC-10 and review carry-over break. Draw a dashed Review record beside the run file. |
| M5 traceability | Ready with changes | Every requirement points to a model and a check | **Fixed now:** test 12 also holds REQ-06, as M1 says. Also done: v3 must also keep AC-06 (survives a redeploy), AC-09 and AC-10, not just AC-04 and AC-05. |

### Risks the pictures don't show

- **Render's free disk is wiped after 15 idle minutes, not only on redeploy.** Changes are "lost on redeploy, restart, or spin-down" ([render.com/docs/free](https://render.com/docs/free)). So even in Phase 3, a `GET /system/analysis/{id}` made after a quiet spell returns 404. That is fine for T-05, which reads straight back, but not for "find the saved result later". Free Render also has no persistent disks, and free Render Postgres expires after 30 days. On this host the only free durable store is the evidence repo written through the Contents API, which pairs naturally with GitHub. The `save`/`load` seam makes that swap one module. `roadmap.md:53` and decision 8 should say "spin-down" too, and cold starts are about a minute, not 30 seconds.
- **Lazy blob fetches.** Slice 5 runs `git ls-tree -r -l` on both full trees. In a blobless clone, `-l` reads every blob's size, and the clone fetches missing blobs one at a time. Look only at changed paths, and let `git diff --numstat` fetch them in one batch and flag binaries.
- **Hunks have no consumer before v4, apart from connector test 1.** The contract and v2 are file-level. Slice 7's `unidiff` dependency and test 1's "one hunk" could wait for v4. That is a choice for Kaan, not a fix.
- **Lockfiles.** M0 sends lockfiles to `skipped[]`, but M3 classifies them as OTHER. Settle this with the pod before slice 8, or the conformance test will show it.

## Edits applied

Kaan chose "Apply all" on 2026-10-17, so items 1 to 3 are now in the roadmap, the guide, the plans, `CONTEXT.md` and the models, and the PNGs are regenerated. Item 4 is for the team:

1. **Roadmap**
   - Slice 1: a separate `/system` app, plain `def` handlers, and the `analyze()` core.
   - Slice 5: drop `ls-tree -l`.
   - Slice 9: `save`/`load` and `runs/` in `.gitignore`.
   - Slice 11: Render facts (spin-down wipes the disk, about a minute to start).
   - Slice 12: add `acceptance.yml`.
   - v3 item 2: the base and head table above, with the merge base from the compare API.
   - v3 item 4: move the webhook wiring to v4.
   - Fix the test count and decision 8.
2. **Guide and plans.** The new-branch row in `github-connector-steps.md` becomes the merge base with the default branch. Mark `commit-fetcher-plan.md`'s stubs table and `documentation-drifter-plan.md:71` as superseded.
3. **Models**
   - The M1, M2, M3, M4 and M5 edits in the table above, with the PNGs regenerated.
   - A box-to-file line in `Models/v1/README.md`.
   - Add "connector", "run store" and "delivery store" to `CONTEXT.md`.
4. **For the team, not for me to change:** the v0 comment at `parse.py:41` (a zero `before` is no longer a first audit, decision 15; done 2026-10-17, the property is now `has_before`), and whether `Source/LLM_Shell/` is the start of the v1.2 LLM work (ask Muhammad).

## Sources

- **Code:** `Source/GitHub_Connector/*.py` and `tests/*.py` at `76eb691`. Test run: `python3 -m pytest -q` gave 18 passed and 1 skipped.
- **Spec:** the end product ([endProduct.txt](../endProduct/endProduct.txt)) §5.3, §6.1, §6.3, §7.3, §8.1–8.2 and review notes 9–11. Also [M0-build-order.pdf](M0-build-order.pdf).
- **GitHub docs:**
  - Events that trigger workflows (pull_request `GITHUB_SHA` is the merge commit, the default activity types, read-only token on fork PRs).
  - Securely using pull_request_target.
  - Control workflow concurrency.
  - Webhook best practices (10-second limit).
  - Handling failed webhook deliveries (no automatic redelivery).
  - REST compare commits (`merge_base_commit`).
  - Reusing workflow configurations (public callers can use only public workflows).
  - The actions/upload-artifact README (retention of 1 to 90 days).
- **Render:** render.com/docs/free (ephemeral filesystem, 15-minute spin-down, about one minute to start, no persistent disks on the free tier).
