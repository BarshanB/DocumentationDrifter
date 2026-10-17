# 03: Requests answered without git: malformed input and unknown runs

**What to build:** A caller who sends a malformed request gets 400 INVALID_REQUEST in an ErrorBody before any git work starts, never FastAPI's 422, and nothing is saved. A caller who asks for an analysis_id that was never saved gets 404, never an empty result.

**Blocked by:** 01 (Tracer: one commit analysed, saved and served back, and a missing repository refused)

**Status:** done. The reference service was probed on 2026-10-17: an unknown or malformed analysis_id gives 404 `{"code": "ANALYSIS_NOT_FOUND", "message": "analysis <id> does not exist"}`, and ours now matches, as do the validation messages.

**Spec:** plan/spec-v1.1.md, user stories 8, 10, 11, 12, 13, 38

- [x] A missing commit_id gives 400 INVALID_REQUEST with the message 'commit_id is required' (AC-07).
- [x] A repository that isn't owner/name gives 400 INVALID_REQUEST. The owner is letters, digits and hyphens; the name also allows dots and underscores. Examples are not-a-repo, three segments, a space, an empty string and an owner containing dots.
- [x] A commit_id that is shorter than 7 characters, longer than 40 or not hex gives 400 INVALID_REQUEST. base_commit follows the same rule when it is given, and an absent or null base_commit is accepted.
- [x] Wrong JSON types, a body that isn't JSON and a missing body each give 400 INVALID_REQUEST with an ErrorBody, never 422.
- [x] Messages use the reference service's wording wherever that wording has been observed.
- [x] With the remote base URL pointed at a location that doesn't exist, every invalid request still gives 400, never REPOSITORY_NOT_FOUND, and no clone is made. This shows that validation runs before git.
- [x] A GET for a well-formed analysis_id with no run file gives 404 with the body the reference service returns in that case. Probe the reference service once for that body and pin it in the test.
- [x] A GET for an id that isn't an- plus 32 hex characters gives the same 404 and reads nothing outside the run store. This includes path-traversal attempts.
- [x] After every failing case the run store holds no run file.
- [x] The whole suite is green, v0 included.
