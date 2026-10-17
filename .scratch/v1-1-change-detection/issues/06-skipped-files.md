# 06: Skipped files: binary, oversize and not UTF-8

**What to build:** A caller sees changed files that couldn't be read as text listed as skipped files in skipped[], each with a reason, and never reported as checked: binary files, files over 1 MB and files that aren't valid UTF-8. The checks run only on changed paths, after one batched fetch of their contents, through a connector file reader that v1.2 will reuse.

**Blocked by:** 01 (Tracer: one commit analysed, saved and served back, and a missing repository refused)

**Status:** ready-for-agent

**Spec:** plan/spec-v1.1.md, user stories 32, 33, 34, 47

- [ ] A changed PNG is in skipped[] with a binary reason. A file counts as binary when git marks it as binary or when its first 8 KB contain a NUL byte.
- [ ] A text file just over 1 MB is skipped with a size reason, and one just under 1 MB stays a change.
- [ ] A changed file that isn't valid UTF-8 is skipped with an encoding reason.
- [ ] The checks read the head side, or the base side for a DELETED change, so a deleted binary is still skipped.
- [ ] A large or binary file that didn't change is not in skipped[].
- [ ] A skipped file is listed only in skipped[], not in changes[], because the connector guide drops binary and oversize files from the listing. Before closing, probe the reference service once with a public commit that changes a binary file, match what it does, and record the answer in the decision log.
- [ ] skipped[] is sorted by path. Reasons are short fixed strings, in the reference service's wording where that wording has been observed.
- [ ] File contents come only from git objects in the temporary clone, fetched in one batch for the changed paths, and nothing is checked out. Inside the scope, the file reader (read) returns a path's content at either side, or nothing where the path is missing on that side. Both points are checked in review.
- [ ] The whole suite is green, v0 included.
