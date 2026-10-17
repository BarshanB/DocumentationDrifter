# 14: Course endpoints: test setup and test report

**What to build:** The course tester can call POST /system/test/setup and GET /system/test/report with the reference service's shapes. A session that was set up returns a report, and an unknown session gets 404 with a message and source system, so both services are graded the same way. The spec schedules this ticket last and work starts only once the pod confirms what the endpoints mean; its only code gate is the conformance harness.

**Blocked by:** 09 (GitHub and the reference service: network smoke test, anonymous not-found, and the conformance harness)

**Status:** ready-for-agent

**Spec:** plan/spec-v1.1.md, user stories 57

- [ ] Before work starts, the semantics the pod confirms are recorded in the decision log: what setup holds, how long a session lives, what the report contains, and how it relates to analyses run during the session.
- [ ] Both routes are on the /system router, with request and response schemas copied from the reference service's OpenAPI, and the offline schema test covers them.
- [ ] A report for an unknown session gives 404 with a body of exactly a message and source system.
- [ ] A malformed setup body, or a missing session_id, gets the status and body that a live probe of the reference service shows. The INVALID_REQUEST mapping is not assumed to apply here.
- [ ] A session that was set up returns a report as the pod described it, and analyses run outside any session are unaffected.
- [ ] Session state is lost on spin-down, like run files, and the README says so.
- [ ] The conformance set gains the unknown-session, malformed-body and setup-then-report cases, compared with ids and timestamps removed.
- [ ] The whole suite is green, v0 included.
