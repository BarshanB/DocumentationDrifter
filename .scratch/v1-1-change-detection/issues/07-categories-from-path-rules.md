# 07: Categories from the ordered path rules

**What to build:** A caller sees every change classified by ordered path rules kept in one rules file, where the first matching rule wins, so code changes can be told apart from doc changes. config_version is a short hash of that file, so any change to the rules shows up in every run file.

**Blocked by:** 01 (Tracer: one commit analysed, saved and served back, and a missing repository refused)

**Status:** done, except the lockfile probe. Lockfiles are OTHER by path; asking the reference service what it does waits for ticket 12, because it can't be reached from this workspace.

**Spec:** docs/plan/spec-v1.1.md, user stories 27, 28, 29, 30, 31

- [x] A reStructuredText file under docs is DOCUMENTATION (T-04). So are Markdown, reStructuredText and plain-text files anywhere, and anything under docs.
- [x] Requirements files such as requirements.txt and requirements-dev.txt are OTHER, because their rule comes before the plain-text rule. A requirements file under docs is OTHER as well.
- [x] Anything under src or tests is IMPLEMENTATION, and so is a Python file anywhere.
- [x] Where rules overlap, rule order decides: a Markdown file under src and a Python file under docs are both DOCUMENTATION.
- [x] Anything else is OTHER, for example a Makefile, an extensionless README or a setup.cfg. There are no DESIGN, ARCHITECTURE, SPECIFICATION or REQUIREMENT rules.
- [x] A renamed file is classified by its new path.
- [ ] Lockfiles are classified by path (done), which makes them OTHER (decision 17, still open). Probe the reference service once with a public commit that changes a lockfile and record its answer under decision 17. If the answer differs, the change follows as its own ticket rather than inside this one.
- [x] config_version stays a short string. The same rules file always gives the same value, and pointing config at an edited rules file gives a different value.
- [x] The tracer's OTHER assertion still holds, and the whole suite is green, v0 included.
