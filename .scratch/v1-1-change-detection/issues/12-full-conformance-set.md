# 12: Full conformance set against the reference service

**What to build:** The conformance test grows to the whole request set: every test-repo label, real public repos and every error case, each sent to both the reference service and ours. Only the agreed known differences may remain. The defaults other tickets took from the spec are confirmed or corrected here.

**Blocked by:** 03 (Requests answered without git: malformed input and unknown runs); 11 (Public test repo with labelled cases)

**Status:** request set built, not run against the reference service, which can't be reached from this workspace. The conformance test now holds Hello-World with and without explicit bases, psf/requests d568f47, every error case and both unknown-run GETs. It adds every test-repo label once DRIFTER_TEST_REPO is set, and checks that each service serves back its own POST bytes. As a dry run on 2026-10-17, our own service stood in as the "reference" and all 15 cases passed, in-process and over DRIFTER_TARGET_URL, so the harness works. What's left needs the live run (CI or any machine that can reach the reference): fix or record each difference with Kaan, record the defaults in the decision log, and tell the pod. Also settle the two open items in the decision log: the code for unexpected git failures, and whether the reference service uses M0's stricter repository pattern. Expect message wording to differ in the error cases, since only "commit_id is required" was ever observed.

**Spec:** plan/spec-v1.1.md, user stories 49, 50, 51

- [x] The request set covers every test-repo label, Hello-World with and without an explicit base, and psf/requests at d568f47.
- [x] It also covers these error cases: a missing commit_id, a malformed repository, a malformed SHA, wrong JSON types, a missing repository, a private repository, an unknown commit, an unknown base_commit, an unfetchable short SHA, and a GET for an unknown or malformed analysis_id.
- [x] For each POST that succeeds on both services, a GET of each service's own analysis_id returns that service's POST bytes.
- [ ] psf/requests at d568f47 matches the reference service's changes[], except that doc files are DOCUMENTATION here and OTHER there.
- [ ] Each difference is either fixed in our service within the contract or recorded as a named known difference. A known difference is recorded only after Kaan agrees, and only for a difference that rests on an open question or on a fault in the reference service. A difference that needs more than a small fix becomes its own ticket.
- [ ] The defaults taken in other tickets are confirmed and recorded in the decision log: whether a skipped file also stays in changes[], how lockfiles are handled (decision 17), the change type for a symlink switch, the wording of skip reasons, and the body of the unknown-run 404.
- [ ] The pod is told that their service returns OTHER for doc files and so fails T-04, along with any other fault found.
- [ ] The whole suite is green both offline and online, v0 included.
