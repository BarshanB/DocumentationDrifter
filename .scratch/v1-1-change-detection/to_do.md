# To do

Items from the 2026-10-17 review of v1.1, left for later. Open questions for the pod are in the [decision log](../../docs/plan/decisions-2026-10-17.md) ("Still open"), and the remaining ticket work is in `.scratch/v1-1-change-detection/issues/`.

## Decided, to build in tickets 12 and 16

- **Match the reference on skipped files** (T12-Q1 and T12-Q2, ticket 16, built 2026-10-17). Left: republish the public test repo, and the live label run against the reference service. Keep skipped files in `changes[]`; add the extension denylist with `UNSUPPORTED_FILE_TYPE` ahead of the content checks, whose reasons become `BINARY_FILE`, `FILE_TOO_LARGE` and `NOT_UTF8`. Hidden paths stay ignored (T12-Q8, T12-Q9). The test repo's expected answers change, so it is republished. This also closes "the skip reason follows the size setting".
- **`tool_version` names the build** (T12-Q5 in the decision log). Report `1.1.0+<first 7 characters of RAILWAY_GIT_COMMIT_SHA>` when it is set, `1.1.0` otherwise; add `tool_version` to `KNOWN_DIFFERENT_FIELDS`; a test sets the variable and checks the result.
- **The no-body setup message** (T12-Q4). Ours stays "body is required", recorded as a known difference resting on a fault in the reference, and reported to the pod with T-04.

## Course routes, left for a complete solution

- **Sessions are never forgotten.** Each `POST /system/test/setup` adds an entry in memory until the process restarts, so anyone could grow it without limit. A cap, or an expiry, would bound it.
- **coverage.py internals.** The report counts statements through `coverage.python.PythonFileReporter`, which coverage.py doesn't document as public. The `coverage==7.6.10` pin holds it; check it on any upgrade.
- **Process-wide monitoring.** Each setup calls `sys.monitoring.restart_events()`, which re-arms every muted line in the process for every monitoring tool. Harmless in the deployed app, but a debugger or coverage run attached to the server would see it.

## Skipped for now

- **Clone failures that aren't "not found"** (review finding e). Every failed clone becomes 404 `REPOSITORY_NOT_FOUND`, including a DNS failure, a GitHub outage or a full disk. A failed fetch by SHA becomes `COMMIT_NOT_FOUND`. Use the 404s only when git reports a missing repository or commit, and settle the code for every other failure together with the open "unexpected git failures" item in the decision log (ticket 12).

## Smaller tidy-ups the review suggested (optional)

- Move the `analyse()` helper, copied into six test files, into `tests/conftest.py`.
- Share one reference-service URL between `ci.yml` and `tests/reference.py`.
- Let `_Git.run` take extra environment variables, instead of `_present` editing `_Git.env` from outside.
