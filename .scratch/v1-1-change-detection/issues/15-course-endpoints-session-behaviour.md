# 15: Course endpoints: session behaviour confirmed by the pod

**What to build:** A course tester who sets up a session and then asks for its report gets the report the pod describes, so both services are graded the same way. This ticket starts only once the pod has confirmed what the endpoints mean.

**Blocked by:** 14 (Course endpoints: the shapes we already know), and the pod's confirmation of the semantics

**Status:** waiting on the pod (becomes ready-for-agent once the semantics are recorded)

**Spec:** plan/spec-v1.1.md, user stories 57

- [ ] Before work starts, the semantics the pod confirms are recorded in the decision log: what setup holds, how long a session lives, what the report contains, and how it relates to analyses run during the session.
- [ ] A session that was set up returns a report as the pod described it.
- [ ] Session state is lost on spin-down, like run files, and the README says so.
- [ ] The conformance set gains the setup-then-report case, compared with ids and timestamps removed.
- [ ] The whole suite is green, v0 included.
