# To do

Items from the 2026-10-17 review of v1.1, left for later. Open questions for the pod are in the [decision log](plan/decisions-2026-10-17.md) ("Still open"), and the remaining ticket work is in `.scratch/v1-1-change-detection/issues/`.

## Waiting for Kaan's decision

- **`tool_version` names the build** (review finding b). Every run reports `1.1.0`, so runs from different deploys can't be told apart (spec user story 6). Railway sets `RAILWAY_GIT_COMMIT_SHA` for deploys triggered from GitHub. Proposed fix: when it is set, report `1.1.0+<first 7 characters>`, and keep `1.1.0` locally. A test sets the variable and checks the result.

## Skipped for now

- **The skip reason follows the size setting** (review finding c). The reason is fixed as "file larger than 1 MB", but `DRIFTER_MAX_FILE_BYTES` can change the limit, which would make the message wrong. Build the message from the setting, or stop making the limit configurable.
- **Clone failures that aren't "not found"** (review finding e). Every failed clone becomes 404 `REPOSITORY_NOT_FOUND`, including a DNS failure, a GitHub outage or a full disk. A failed fetch by SHA becomes `COMMIT_NOT_FOUND`. Use the 404s only when git reports a missing repository or commit, and settle the code for every other failure together with the open "unexpected git failures" item in the decision log (ticket 12).

## Smaller tidy-ups the review suggested (optional)

- Move the `analyse()` helper, copied into six test files, into `tests/conftest.py`.
- Share one reference-service URL between `ci.yml` and `tests/reference.py`.
- Let `_Git.run` take extra environment variables, instead of `_present` editing `_Git.env` from outside.
