# 15: Course endpoints: session behaviour confirmed by the pod

**What to build:** A course tester who sets up a session and then asks for its report gets the report the pod describes, so both services are graded the same way. This ticket starts only once the pod has confirmed what the endpoints mean.

**Blocked by:** 14 (Course endpoints: the shapes we already know), and the pod's confirmation of the semantics

**Status:** built ahead of the pod's confirmation, by Kaan's choice (2026-10-17), from what the reference service was seen to do: a report counts the executable lines of the code that ran on any request since the session's setup, measured on our v1 modules with Python line events and coverage.py's statement lines. Left: the pod confirming the semantics recorded in the decision log.

**Spec:** docs/plan/spec-v1.1.md, user stories 57

- [ ] Before work starts, the semantics the pod confirms (observed semantics recorded on 2026-10-17; the pod's confirmation is still to come) are recorded in the decision log: what setup holds, how long a session lives, what the report contains, and how it relates to analyses run during the session.
- [x] A session that was set up returns a report as the reference service was seen to (the pod still to confirm).
- [x] Session state is lost on spin-down, like run files, and the README says so.
- [x] The conformance set gains the setup-then-report case, compared with ids and timestamps removed.
- [x] The whole suite is green, v0 included.
