# 08: Limits and lost writes: TIMEOUT, the concurrency cap and WRITE_FAILED

**What to build:** A slow analysis fails with 500 TIMEOUT instead of hanging the service: each git call is capped at 60 s and the whole analysis at 120 s. At most two analyses run at once, and extra requests wait their turn. A run file that can't be written gives 500 WRITE_FAILED, so a lost run is never reported as saved, and all three limits come from config.

**Blocked by:** 01 (Tracer: one commit analysed, saved and served back, and a missing repository refused)

**Status:** ready-for-agent

**Spec:** plan/spec-v1.1.md, user stories 38, 39, 40, 41, 42, 44

- [ ] A tiny configured analysis deadline gives 500 TIMEOUT in an ErrorBody.
- [ ] A tiny configured git-call timeout gives 500 TIMEOUT in the same way, and the git process is stopped rather than left running.
- [ ] With the concurrency limit set to 1, two simultaneous requests both succeed: the second waits instead of failing. The limit sits around the whole analysis, so time spent waiting for a slot doesn't count against the deadline.
- [ ] The defaults are 60 s per git call, 120 s per analysis and 2 analyses at once. Each can be changed in config without touching code.
- [ ] When the run store location can't be written, POST gives 500 WRITE_FAILED with an ErrorBody. No partial run file is left, and nothing can be fetched for that analysis.
- [ ] A SUCCESS answer always means GET can fetch its run file.
- [ ] After each of these failures, no run file is saved and no temporary clone remains, even when git was stopped mid-clone.
- [ ] The whole suite is green, v0 included.
