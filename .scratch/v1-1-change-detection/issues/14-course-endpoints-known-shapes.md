# 14: Course endpoints: the shapes we already know

**What to build:** The course tester can call POST /system/test/setup and GET /system/test/report on our service and get the same request and response shapes as the reference service, including 404 with a message and source system for an unknown session. This covers only what has already been seen on the reference service. What a session holds and what a report contains is ticket 15 (Kaan split the ticket, 2026-10-17).

**Blocked by:** 09 (GitHub and the reference service: network smoke test, anonymous not-found, and the conformance harness)

**Status:** ready-for-agent

**Spec:** plan/spec-v1.1.md, user stories 57

- [ ] Both routes are on the /system router, with request and response schemas copied from the reference service's OpenAPI, and the offline schema test covers them.
- [ ] A report for an unknown session gives 404 with a body of exactly a message and source system.
- [ ] A malformed setup body, or a missing session_id, gets the status and body that a live probe of the reference service shows. The INVALID_REQUEST mapping is not assumed to apply here.
- [ ] A well-formed setup request is accepted with the status and response shape a live probe of the reference service shows. Nothing beyond that is assumed about what setup does.
- [ ] Analyses run outside any session are unaffected by these routes.
- [ ] The conformance set gains the unknown-session and malformed-body cases.
- [ ] The whole suite is green, v0 included.
