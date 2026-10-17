# 09: GitHub and the reference service: network smoke test, anonymous not-found, and the conformance harness

**What to build:** With no override, the service analyses a real public repo on GitHub, and it refuses missing and private repositories with 404 REPOSITORY_NOT_FOUND without ever using the host's credentials. A maintainer can run a conformance test that sends the same requests to the reference service and to ours and fails on any difference beyond the known ones. A schema test pins our published contract to the reference service's.

**Blocked by:** 01 (Tracer: one commit analysed, saved and served back, and a missing repository refused)

**Status:** ready-for-agent

**Spec:** plan/spec-v1.1.md, user stories 2, 14, 49, 50, 51

- [ ] All network tests share one skip marker. A quick reachability check skips them when GitHub can't be reached, and they also skip when the suite is told to stay offline (the switch the PR workflow sets). The local suite always runs.
- [ ] octocat/Hello-World at 7fd1a60, through the default remote base URL, returns head_commit 7fd1a60b… and base_commit 553c2077…, its first parent, with the README change as MODIFIED. The run file is saved and can be fetched.
- [ ] A repository that can't exist on GitHub gives 404 REPOSITORY_NOT_FOUND within a few seconds and with no prompt, and so does a private repository the team owns. A credential helper is set up for the test process to record any use, and it is never called. If the test host injects credentials outside git's control, record that, and also run the private-repo check somewhere nothing is injected (CI or the deployed service).
- [ ] A captured copy of the reference service's OpenAPI document is kept as test data. An offline test compares it with our AnalysisRequest, AnalysisResult, Change, Finding, Skipped and ErrorBody. The only allowed difference is DOCUMENTATION in the category enum; Finding has no confidence field, and LLM_UNAVAILABLE is not yet an error code. A network test runs the same comparison against the live document.
- [ ] The conformance test first warms the reference service through its health route, with retries. It then sends each request to both services, removes analysis_id and created_at, and compares status codes and bodies. Any other difference fails with a readable diff that names the field.
- [ ] The allowed differences are listed in one place: DOCUMENTATION where the reference service says OTHER for doc files, and config_version. The list can't be widened for a single case. tool_version is removed before comparing, like analysis_id and created_at, because it is a build label (Kaan, 2026-10-17).
- [ ] 'Ours' is the in-process app by default, or a deployed URL taken from test config, so the acceptance workflow can reuse the harness.
- [ ] The starting request set is Hello-World, a missing repository, a private repository and GET health, and every case matches.
- [ ] The whole suite is green both offline and online, v0 included.
