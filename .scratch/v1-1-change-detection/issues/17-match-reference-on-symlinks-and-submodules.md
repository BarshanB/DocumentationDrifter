# 17: Match the reference on symlinks and submodules

**What to build:** A caller gets the same `changes[]` and `skipped[]` as the reference service for commits that touch symlinks and submodules. A new, deleted or renamed symlink or submodule is listed in `changes[]` with its change type and category, and is also listed in `skipped[]` as `UNSUPPORTED_FILE_TYPE`, since we never read it. A switch between a regular file and a symlink is one TYPE_CHANGED change in either direction, and is not skipped.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent · decided on 2026-10-17 (decision log, T12-Q10)

**Spec:** docs/plan/spec-v1.1.md, user stories 25, 32, 33 (as amended by T12-Q10)

- [ ] The test repo's `symlink` label lists `link-to-readme` in `changes[]` (ADDED, OTHER) and in `skipped[]` as `UNSUPPORTED_FILE_TYPE`, as the reference does.
- [ ] The `submodule` label lists `vendor/lib` the same way, and `mixed` does so for `mixlink` and `vendor/other`.
- [ ] The `file-to-symlink` label gives one TYPE_CHANGED change for `switchy.txt`, which isn't skipped, and `symlink-to-file` still does.
- [ ] Hidden paths stay ignored even when they are symlinks or submodules (T12-Q9).
- [ ] The rule lives in the connector, not in the rules file: these are skipped by what git says they are (mode `120000` or `160000`), whatever their extension.
- [ ] `LINK_PATHS` in `tests/reference.py` is removed, and with DRIFTER_LABEL_CONFORMANCE=1 every label matches the reference apart from the recorded known differences.
- [ ] M3's diagram and its PNG, roadmap decision 5's wording and spec story 25 match the new rule, and the test repo's expected answers are updated in `tools/testrepo.py`, ready for Kaan to republish.
- [ ] The whole suite is green offline and online.
