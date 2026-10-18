# 13: Manual acceptance workflow against the deployed service

**What to build:** A maintainer starts a manual workflow that warms the deployed service through GET /system/health, then runs T-01 to T-07 on the test repo and the conformance test against the deployed URL, so the public service is checked the way the course tester will check it. It is the dry run for the v3 Action.

**Blocked by:** 10 (Public deployment on Railway's free plan); 12 (Full conformance set against the reference service)

**Status:** done (2026-10-18). A manual run on `main` against https://documentationdrifter-production.up.railway.app/system passed every step (Actions run 39102903374): warm-up, the 23 labels for T-01 to T-07, and the conformance set. The workflow now sets DRIFTER_LABEL_CONFORMANCE=1, since tickets 16 and 17 settled the ticket 12 differences; run locally against the deploy, all 56 conformance cases with the labels matched the reference.

**Spec:** docs/Models/v1/v1.1/spec-v1.1.md, user stories 54

- [x] The workflow runs on manual dispatch, with an optional schedule, and has read-only access to contents.
- [x] Its warm-up retries health long enough to ride out a cold start of about a minute, and fails with a clear message if the service never answers.
- [x] T-01 to T-07, driven by test-repo labels, and the conformance test run against a target URL that the workflow sets. When no target is set, the same tests run against the in-process app.
- [x] Each POST is followed at once by a GET of its analysis_id, which returns identical bytes; this matters because run files vanish on spin-down.
- [x] A failure in either suite fails the run. Once Kaan approves the push, a manual run passes against the deployed URL.
