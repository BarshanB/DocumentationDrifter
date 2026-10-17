# 13: Manual acceptance workflow against the deployed service

**What to build:** A maintainer starts a manual workflow that warms the deployed service through GET /system/health, then runs T-01 to T-07 on the test repo and the conformance test against the deployed URL, so the public service is checked the way the course tester will check it. It is the dry run for the v3 Action.

**Blocked by:** 10 (Public deployment on Railway's free plan); 12 (Full conformance set against the reference service)

**Status:** ready to run: the push (02), the deploy (10) and the public test repo (11) are all done, and the workflow now defaults DRIFTER_TEST_REPO to kaan-kanadasi/DocumentationDrifter-testrepo. Run it with target_url https://documentationdrifter-production.up.railway.app/system. Expect its conformance step to fail on the labels until Kaan settles the three ticket 12 differences (skipped files kept in changes[], skips by file type, hidden paths); T-01 to T-07 against our service should pass.

**Spec:** plan/spec-v1.1.md, user stories 54

- [x] The workflow runs on manual dispatch, with an optional schedule, and has read-only access to contents.
- [x] Its warm-up retries health long enough to ride out a cold start of about a minute, and fails with a clear message if the service never answers.
- [x] T-01 to T-07, driven by test-repo labels, and the conformance test run against a target URL that the workflow sets. When no target is set, the same tests run against the in-process app.
- [x] Each POST is followed at once by a GET of its analysis_id, which returns identical bytes; this matters because run files vanish on spin-down.
- [ ] A failure in either suite fails the run. Once Kaan approves the push, a manual run passes against the deployed URL.
