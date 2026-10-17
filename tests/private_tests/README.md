# Private-repo tests

These tests check that our service refuses a **private** repository with 404 `REPOSITORY_NOT_FOUND` (spec user story 14, tickets 09 and 12) and never uses the host's GitHub credentials. They use our own repo, `MuhammadSban/DocumentationDrifter`, as the private example.

**When they run.** Only while that repo is private. Each test first asks GitHub's API, without credentials, whether the repo is public or private:

- **Private:** the tests run.
- **Public:** the tests skip with "…is public, so the private-repo checks don't apply". The repo has been public since 2026-10-17, to make deployment easier; while it is, [`tests/public_tests`](../public_tests/README.md) checks the opposite case.
- **Unknown** (no network): the tests skip.

Nothing needs changing if the repo goes private again; these tests pick that up on their own.

**Anonymous hosts.** A private repo is only a fair test where nothing adds GitHub credentials behind git's back. Before the not-found check, the tests try a bare anonymous `git ls-remote` of the repo. If that succeeds, the host injects credentials (Claude's cloud workspace does, for example), and the test skips. In CI, `DRIFTER_REQUIRE_ANONYMOUS=1` turns that skip into a failure, and the checkout runs with `persist-credentials: false`.

**What runs here:**

- `test_private_repository_is_not_found`: 404 `REPOSITORY_NOT_FOUND`, and a credential helper planted in git's environment is never called.
- `test_private_repository_conformance`: the same request gets the same answer from the reference service (needs it to be reachable; `DRIFTER_REQUIRE_REFERENCE=1` makes an outage fail).
