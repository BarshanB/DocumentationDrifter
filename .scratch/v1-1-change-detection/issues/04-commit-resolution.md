# 04: Commit resolution: short SHAs, commits off every branch, odd bases and first audits

**What to build:** A caller can name the head commit and base commit by full or short SHA and gets both back as full SHAs, and a commit that no branch reaches is fetched by SHA. Any base_commit is compared exactly as given, and a root commit with no base is a first audit. An unknown commit, or a short SHA that can't be fetched or is ambiguous, gives 404 COMMIT_NOT_FOUND; when the SHA was short, the message asks for the full 40-character SHA.

**Blocked by:** 01 (Tracer: one commit analysed, saved and served back, and a missing repository refused)

**Status:** done

**Spec:** docs/plan/spec-v1.1.md, user stories 1, 15, 16, 17, 19, 20, 21, 38, 44

- [x] A base_commit several commits behind the head gives the changes across all of those commits, not just the head's own, and base_commit comes back as the full SHA.
- [x] A base_commit equal to the head gives 200 SUCCESS with an empty changes[], and the run file is saved and can be fetched like any other.
- [x] A base_commit after the head gives the reverse listing, exactly as asked, so a file the head doesn't have is DELETED. A base_commit from unrelated history in the same repo, such as a second root commit, gives SUCCESS with whatever comparing the two commits yields.
- [x] A root head commit with no base_commit gives base_commit null and every file ADDED, compared against the empty tree (first audit). A merge commit with no base_commit is compared against its first parent.
- [x] A 7-character commit_id and a 7-character base_commit both come back as full 40-character SHAs.
- [x] A full SHA of a commit that no branch or tag reaches is fetched by SHA and analysed with SUCCESS. The fixture allows that fetch, as GitHub does.
- [x] An unknown full commit_id gives 404 COMMIT_NOT_FOUND (AC-08). So does an unknown full base_commit, and so does a SHA that names something other than a commit.
- [x] A short SHA of the unreachable commit gives 404 COMMIT_NOT_FOUND with a message asking for the full 40-character SHA, and so does a short SHA that two commits share. The shared-prefix fixture needs many generated commits, so it is built once per test session.
- [x] None of these errors saves a run file or leaves a clone behind.
- [x] The whole suite is green, v0 included.
