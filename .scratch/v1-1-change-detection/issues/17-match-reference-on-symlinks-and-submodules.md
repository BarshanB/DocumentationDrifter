# 17: Match the reference on symlinks and submodules

**What to build:** A caller gets the same `changes[]` and `skipped[]` as the reference service for commits that touch symlinks and submodules. A new, deleted or renamed symlink or submodule is listed in `changes[]` with its change type and category, and is also listed in `skipped[]` as `UNSUPPORTED_FILE_TYPE`, since we never read it. A switch between a regular file and a symlink is one TYPE_CHANGED change in either direction, and is not skipped.

**Blocked by:** None (can start immediately)

**Status:** done except the republish (2026-10-17). Symlinks and submodules outside hidden paths are listed in `changes[]` with a category from the path rules and skipped as `UNSUPPORTED_FILE_TYPE`, judged by git's mode in `fetch.py`; a modified symlink or a submodule bump follows the same rule (MODIFIED and skipped), and a switch between a regular file and a symlink or submodule is one TYPE_CHANGED change that isn't skipped. `tree(side)` still lists regular files only. With DRIFTER_LABEL_CONFORMANCE=1 all 23 labels matched the reference live from Kaan's machine, and the whole suite passed online (239 passed; the two symlink tests that need filesystem symlinks skip on this Windows machine, the labels cover them through fast-import). The modified-symlink, submodule-bump and file-to-submodule cases were never probed on the reference. Left: Kaan republishes the test repo for the new expected answers.

**Spec:** docs/plan/spec-v1.1.md, user stories 25, 32, 33 (as amended by T12-Q10)

- [x] The test repo's `symlink` label lists `link-to-readme` in `changes[]` (ADDED, OTHER) and in `skipped[]` as `UNSUPPORTED_FILE_TYPE`, as the reference does.
- [x] The `submodule` label lists `vendor/lib` the same way, and `mixed` does so for `mixlink` and `vendor/other`.
- [x] The `file-to-symlink` label gives one TYPE_CHANGED change for `switchy.txt`, which isn't skipped, and `symlink-to-file` still does.
- [x] Hidden paths stay ignored even when they are symlinks or submodules (T12-Q9).
- [x] The rule lives in the connector, not in the rules file: these are skipped by what git says they are (mode `120000` or `160000`), whatever their extension.
- [x] `LINK_PATHS` in `tests/reference.py` is removed, and with DRIFTER_LABEL_CONFORMANCE=1 every label matches the reference apart from the recorded known differences.
- [x] M3's diagram and its PNG, roadmap decision 5's wording and spec story 25 match the new rule, and the test repo's expected answers are updated in `tools/testrepo.py`, ready for Kaan to republish.
- [x] The whole suite is green offline and online.
