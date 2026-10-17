# 02: CI runs the whole suite on every PR

**What to build:** A maintainer who opens a PR gets a check that runs the whole test suite from the repo root with read-only permissions, so a red change can't merge unnoticed. It can land on day one with the v0 suite, and it picks up every v1 test as that test lands.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

**Spec:** plan/spec-v1.1.md, user stories 53

- [ ] A workflow runs on every pull request. It installs the pinned requirements on a runner that has git, then runs pytest quietly from the repo root. Its only permission is read access to contents.
- [ ] The v0 suite passes there (18 pass, 1 skips without the local environment file), along with every v1 test that exists when the workflow lands. No step is specific to v1, so the fixture repo tests run there as soon as they land.
- [ ] The PR run includes the network tests: the GitHub smoke test and the conformance test against the reference service run on every PR (Kaan, 2026-10-17: a push is a meaningful change, so it gets the full check). The workflow warms the reference service through its health endpoint first, with retries, so a sleeping service is woken before the tests run.
- [ ] A test made to fail on purpose on a throwaway branch turns the check red.
- [ ] Once Kaan approves the push, a PR shows a green check.
