# 14: Course endpoints: the shapes we already know

**What to build:** The course tester can call POST /system/test/setup and GET /system/test/report on our service and get the same request and response shapes as the reference service, including 404 with a message and source system for an unknown session. This covers only what has already been seen on the reference service. What a session holds and what a report contains is ticket 15 (Kaan split the ticket, 2026-10-17).

**Blocked by:** 09 (GitHub and the reference service: network smoke test, anonymous not-found, and the conformance harness)

**Status:** done (2026-10-17). Every shape was probed on the reference service first: 201 `{session_id}`, 409 for a repeated id, 400 and 404 bodies of `{message, source: "system"}` with the reference's exact messages, and `TestSetupRequest` copied field for field. Twelve error cases and a setup-then-report case joined the conformance set (the report compared by keys and value types, since the counts describe two codebases), and the first nine and the setup flow matched the reference when checked from Chrome; the other three were probed by hand with the same answers. One deliberate difference: a setup with no body answers "body is required", where the reference says " is required" with an empty field name. It is not in the conformance set until Kaan agrees to record it.

**Spec:** plan/spec-v1.1.md, user stories 57

- [x] Both routes are on the /system router, with request and response schemas copied from the reference service's OpenAPI, and the offline schema test covers them. (The reference declares no response schemas, so neither do we. Its document was captured on 2026-10-17 into tests/data/reference-openapi.json, checked byte for byte against a SHA-256 taken in the browser.)
- [x] A report for an unknown session gives 404 with a body of exactly a message and source system.
- [x] A malformed setup body, or a missing session_id, gets the status and body that a live probe of the reference service shows. The INVALID_REQUEST mapping is not assumed to apply here.
- [x] A well-formed setup request is accepted with the status and response shape a live probe of the reference service shows. Nothing beyond that is assumed about what setup does.
- [x] Analyses run outside any session are unaffected by these routes.
- [x] The conformance set gains the unknown-session and malformed-body cases.
- [x] The whole suite is green, v0 included.
