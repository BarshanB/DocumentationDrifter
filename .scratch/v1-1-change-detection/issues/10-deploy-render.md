# 10: Public deployment on Render's free tier

**What to build:** The course tester can reach the service at a public URL. A container image with git installed serves only the v1 app, with the source folder as the app directory, and is deployed to Render's free tier; GET /system/health is the warm-up call. The README warns operators that idle spin-down wipes run files.

**Blocked by:** 01 (Tracer: one commit analysed, saved and served back, and a missing repository refused)

**Status:** ready-for-agent

**Spec:** plan/spec-v1.1.md, user stories 9, 55, 56

- [ ] The image builds locally, includes git and holds no credentials. Its run store location is writable.
- [ ] The container serves only the v1 app; v0's webhook routes can't be reached.
- [ ] Run locally, the container answers health and analyses octocat/Hello-World at 7fd1a60 through the default remote base URL.
- [ ] With the container held to 512 MB, two simultaneous analyses of a small public repo both finish.
- [ ] Once Kaan approves the push and the Render setup, the service answers health at its public URL within about a minute of waking. A POST for Hello-World succeeds, and an immediate GET of its analysis_id returns the same bytes.
- [ ] The README gives the public URL and names health as the warm-up call. It says the free tier spins down after 15 idle minutes and takes about a minute to wake. It also says run files are wiped on spin-down, restart and redeploy, so a GET for an old run can return 404 on both teams' services and isn't a bug.
- [ ] The whole suite is green, v0 included.
