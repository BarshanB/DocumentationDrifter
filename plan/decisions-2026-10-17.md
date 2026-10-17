# Decision log: grilling session, 2026-10-17

Kaan answered eighteen questions about v1 on 2026-10-17. Each entry gives the question, the answer and the reason for it. The [roadmap](roadmap.md) carries the same decisions in its v1 section and its decisions table (rows 4, 16 and 18–22).

## Scope and the LLM

**Q1 · LLM at runtime.** Should v1 keep the LLM out of the running system, as [phase2.pdf](phase2.pdf) §7, §8.2 and §9.1 say?
**Answer:** No. An LLM is the component that decides drift.
**Why:** Kaan's direction for the project is that the LLM makes the drift call. This overrides the spec's "GenAI will not be part of the running system".

**Q9 · When the LLM comes in.** Which version brings the LLM in?
**Answer:** v1, split in two. v1.1 is git change detection only, and v1.2 adds the LLM. In v1.2 the LLM is probabilistic on purpose; the final version is deterministic.
**Why:** Getting the git half working and matching the reference service first gives a solid base. The LLM then goes on top of output that is already tested.

**Q10 · Mapping file.** Does v1.2 need an authored mapping file of which doc covers which code?
**Answer:** No. Neither v1.1 nor v1.2 has one. The LLM reads the changed files and the repo's doc files directly. The mapping comes in v1.3 if time allows, otherwise in v2.
**Why:** It keeps v1.2 small. A mapping can narrow what the LLM reads once it exists.

**Q11 · LLM provider (replaced by Q18).** Use the Claude API, with the key on Render?
**Answer:** Yes at first, then replaced by Q18.
**Why:** Render's free tier (512 MB) can't run a local model, so the LLM has to be a hosted API. Q18 then picked a free one.

**Q18 · Starting provider.** Which LLM provider does v1.2 start on?
**Answer:** Google Gemini's free tier (a Gemini Flash model, 1M-token context), behind one function, with the provider and model set in config and the key in a Render environment variable.
**Why:** It is free while v1.2 is experimental, and its context easily holds the 200 KB doc budget. Moving to Claude Haiku 5.5 (under 1¢ per analysis) or another provider later is a config change. Google can change the free tier's daily limits, and a rate-limited call fails the analysis (Q16).

**Q15 · Model choice (withdrawn).** Use Claude Sonnet 5.5?
**Answer:** Withdrawn after Q18, since v1.2 starts on Gemini.
**Why:** The question applied only to the Claude API.

**Q12 · Repeat-run matching.** Relax AC-10 and the conformance test for `issues[]` in v1.2?
**Answer:** Yes. `changes[]` must still match exactly. For `issues[]` the tests check only the shape: each finding names a real changed file and a real doc file, and has a valid issue type. The exact check returns in the final version.
**Why:** A probabilistic LLM can give different findings on the same input, so an exact check would fail at random and say nothing. `changes[]` comes from git, so it can stay strictly tested.

**Q13 · Confidence field.** Add a confidence score to `Finding`?
**Answer:** No. `Finding` keeps the reference service's shape, and the LLM's reasoning goes in `explanation`.
**Why:** Adding a field changes the contract we share with the pod and could break their tester.

**Q14 · What the LLM reads.** Send every doc file at head, up to 200 KB in total?
**Answer:** Yes. The cap is a config value. Docs past it go to `skipped[]` with an "over doc budget" reason.
**Why:** 200 KB is about 50,000 tokens. It fits in one call with room for the changed code, and most class-sized repos have less. A larger cap costs more time and money per analysis and pushes against the 120 s deadline (Q7). Whatever isn't sent is listed as skipped, never reported as checked.

**Q16 · LLM failure.** Fail the whole analysis when the LLM call fails?
**Answer:** Yes. It returns 500 `LLM_UNAVAILABLE` and saves nothing. This error code is new, beyond the pod's contract.
**Why:** Returning SUCCESS with an empty `issues[]` would look like "no drift found" when the docs were never checked (REQ-05).

## Git change detection (v1.1)

**Q2 · Hunks.** Drop line-level hunks (`git diff -U0` and `unidiff`) from v1?
**Answer:** Yes. Connector test 1 now checks only for one MODIFIED change.
**Why:** Nothing in the contract or v2 reads hunks, so they were a dependency with no user. v1.2 can still hand the plain `git diff` text to the LLM.

**Q3 · Copies.** Detect COPIED changes?
**Answer:** No. Renames only, using `-M` at git's default 50% similarity, so COPIED never appears.
**Why:** Adding `-C` could turn plain ADDED files into COPIED ones and disagree with the reference service. The conformance test shows what the pod does, and switching later is a one-flag change.

**Q4 · Renames across the hidden-path rule.** How are renames into or out of a hidden path reported?
**Answer:** Each side is filtered separately. `.github/a.md` → `docs/a.md` is ADDED, and `docs/x.md` → `.archive/x.md` is DELETED.
**Why:** The rule that hidden paths never appear stays absolute, even as `old_path`.

**Q5 · Unusual base commits.** Accept any `base_commit`?
**Answer:** Yes, and diff exactly what was given. A base equal to the head gives an empty `changes[]` and SUCCESS. A base after the head, or from unrelated history, gives whatever `git diff base head` says.
**Why:** The API stays simple and predictable. Choosing a sensible base is the caller's job, and the v3 Action does that.

**Q6 · Short SHAs.** What happens to a short SHA that can't be fetched, or that matches more than one commit?
**Answer:** 404 `COMMIT_NOT_FOUND`, with a message asking for the full 40-character SHA.
**Why:** GitHub only lets you fetch a commit that isn't on a branch or tag by its full SHA. Reusing an existing contract error code adds nothing new, and the Action always sends full SHAs anyway.
**Update (2026-10-17, after the first conformance run):** the reference service answers the same case with "commit 1234567 was not found in owner/name". Kaan kept our message; it is the one named known difference in `tests/reference.py` (`KNOWN_CASE_DIFFERENCES`). Every other message, the unknown-run body (`ANALYSIS_NOT_FOUND`) and the schema now match the reference service.

**Q7 · Time limits and concurrency.** What deadline, git timeout and number of simultaneous analyses?
**Answer:** 120 s per analysis, 60 s per git call, and two analyses at once, all in config.
**Why:** Two blobless clones fit in Render's free-tier 512 MB, and the values can change without code changes.

## Project vocabulary

**Q8 · Glossary location.** Commit CONTEXT.md to the repo, and define the pod's service?
**Answer:** Yes. CONTEXT.md sits at the repo root and defines **Reference service**: the pod's live v1 service that our output must match.
**Why:** The glossary then lives with the code it describes, and "the pod" was being used without a definition.

**Q17 · Planning files in the repo.** Commit `plan/` and `Models/v1/`?
**Answer:** Yes, on the `kaan_v1` branch, with no merge until Kaan says so.
**Why:** Teammates can then work from the same plan and decisions on GitHub.

## Later the same day

**Hosting (roadmap decision 8).** Render's free tier needs a card on file, and the card wouldn't verify, so Kaan moved hosting to Railway, whose Free plan needs no card. Where Q7, Q11 and Q18 above mention Render, read Railway: the Gemini key goes in a Railway environment variable, and two clones fit in its 0.5 GB.

**Probed later the same day (Kaan's Chrome, against the reference service).**

*Course routes (tickets 14 and 15).* `POST /system/test/setup` takes `TestSetupRequest` (`session_id`: 1 to 200 characters, required; `setup`: any object, optional; extra fields ignored) and answers 201 `{"session_id"}`. A repeated id is 409 "session X already exists". `GET /system/test/report?session_id=` answers 400 "session_id query parameter is required" without an id, 404 "session X is unknown" for one never set up, and otherwise 200 `{"session_id", "coverage": {"code": {"covered", "total", "basis"}}}`. Every error body is `{"message", "source": "system"}`, and setup's validation messages copy analyze's style ("session_id is required", "session_id has the wrong type", "setup has the wrong type", "body has the wrong type", and pydantic's own wording for the length limits). The report counts executable lines of their package that ran while handling *any* request since the session's setup, not only requests that name the session: an analysis sent with no session id raised the count as much as one sent with it. Kaan chose to build the real report now (2026-10-17). Ours counts the v1 modules of `GitHub_Connector` (v0's webhook files never run in the `/system` app) with Python line events and coverage.py's statement lines, so `total` and `covered` differ from theirs by design. A setup with no body is the one message we didn't copy: theirs says " is required" with an empty field name, ours says "body is required". Kaan to agree before it becomes a known difference. The pod still has to confirm these semantics.

*Ticket 12 probes.* Seven public commits went to both services: `psf/requests` 0a760ff0 (Pipfile.lock), `pallets/flask` ff6fa22f (uv.lock and more), `pallets/flask` 40e0024d (a small PNG), `encode/httpx` d4961b9f (a 1.9 MB PNG), `psf/requests` 724ae127 (a 2.1 MB text .ai file), `psf/requests` 784fe8bb (a non-UTF-8 .ai file) and `pallets/flask` ac302fb6 (CHANGES.rst whose old version isn't UTF-8). Base commits matched every time. Three behaviours differ:

1. **A skipped file stays in `changes[]` on theirs**, and is listed again in `skipped[]`. Ours leaves it out of `changes[]`, as the connector guide says.
2. **They skip by file type, with a code as the reason.** Every reason seen was `UNSUPPORTED_FILE_TYPE`: `.lock` lockfiles, `.png`, `.svg`, `.ai` and `.html` were skipped, while `.py`, `.rst`, `.toml`, `.yml` and `.yaml` were not, whatever their size or encoding (the 2.1 MB `.ai` and the non-UTF-8 `.ai` got the same code, and the non-UTF-8 CHANGES.rst wasn't skipped). Ours skips by content, with the reasons "binary file", "file larger than 1 MB" and "not valid UTF-8", and lockfiles are ordinary OTHER files. This answers roadmap decision 17: on theirs a lockfile is OTHER in `changes[]` and also skipped.
3. **They list hidden paths.** `.github/workflows/*.yaml` and `.pre-commit-config.yaml` appear in their `changes[]`; our hidden-path rule (spec story 25, roadmap decisions 9 and 19) drops them.

Also seen, and already allowed: `docs/overrides/partials/nav.html` is DOCUMENTATION here and OTHER there. No public commit switching a symlink to a file was found, so that probe waits for the test repo (ticket 11).

## Still open

- **Skipped files, skip reasons and hidden paths:** match the reference service on the three differences above, record them as known differences, or ask the pod which one is meant (Kaan to decide; probed 2026-10-17). Lockfiles (roadmap decision 17) follow whatever is chosen for skip reasons.
- **`/test` endpoints:** built from what the reference service was seen to do (above); the pod still has to confirm the semantics.
- **Unexpected git failures:** a git call that fails in a way the connector doesn't foresee (not a timeout, a missing repository or an unknown commit) returns FastAPI's plain-text 500 instead of an `ErrorBody`, and none of the five contract codes fits. Ask the pod what code their service uses, and settle it in ticket 12 (Kaan, 2026-10-17).
- **Repository pattern:** [M0](M0-build-order.pdf) uses `^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[\w.-]{1,100}$`, stricter than the spec's `^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$`. The spec's pattern stays until the conformance run shows what the reference service accepts (Kaan, 2026-10-17).
