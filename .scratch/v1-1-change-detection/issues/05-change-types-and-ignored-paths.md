# 05: Change types and ignored paths

**What to build:** A caller sees each changed file once, as ADDED, MODIFIED, DELETED or RENAMED. A rename is one RENAMED change that carries old_path, copies are never reported, and every change is returned however many files the commit touches. Hidden paths, symlinks and submodules are ignored paths that never appear anywhere, not even as old_path, because each side of a rename is checked on its own.

**Blocked by:** 01 (Tracer: one commit analysed, saved and served back, and a missing repository refused)

**Status:** done (a symlink-to-file switch follows M3 and shows as TYPE_CHANGED until ticket 12 pins what the reference service does)

**Spec:** docs/Models/v1/v1.1/spec-v1.1.md, user stories 22, 23, 24, 25, 26, 36, 47

- [x] A moved file, unchanged or lightly edited, gives one RENAMED change, with path set to the new path and old_path to the old one, not a delete plus an add (T-03). A move below git's default 50% similarity gives one DELETED change and one ADDED change.
- [x] A copy of an existing file, with the original kept, gives ADDED, and COPIED never appears. Every change that isn't a rename has old_path null.
- [x] A commit with 301 or more changed files returns every one of them, sorted by path.
- [x] The change-type cases behind T-01, T-02, T-06 and T-07 pass through fixture repos.
- [x] A commit that adds a root dotfile, a Markdown file in a hidden folder and a Python file under src lists only the Python file. A hidden segment anywhere in a path makes it an ignored path, including a dot-folder deep inside an ordinary folder.
- [x] A symlink is neither listed nor read, and a submodule is not listed. An executable regular file is kept.
- [x] A rename out of a hidden folder into docs is one ADDED change with old_path null, and a rename from docs into a hidden folder is one DELETED change (decision 19).
- [x] When a file switches between regular file and symlink, the symlink side is never listed or read. The change type reported for this case is not assumed here; it is pinned in the full conformance run.
- [x] Inside the connector's scope, the per-side file listing (tree) applies the same filter and does not read blob sizes, so listing a blobless clone fetches no blobs. This is checked in review, since v1.2 is the listing's first user.
- [x] The whole suite is green, v0 included.
