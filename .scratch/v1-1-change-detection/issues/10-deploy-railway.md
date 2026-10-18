# 10: Public deployment on Railway's free plan (moved from Render, decision 8)

**What to build:** The course tester can reach the service at a public URL. A container image with git installed serves only the v1 app, with the source folder as the app directory, and is deployed to Railway's free plan; GET /system/health is the warm-up call. The README warns operators that idle spin-down wipes run files.

**Blocked by:** 01 (Tracer: one commit analysed, saved and served back, and a missing repository refused)

**Status:** done. Deployed on Railway on 2026-10-17 from `main` (25e4d06, then 954459a with the course routes) at https://documentationdrifter-production.up.railway.app, port 8080. Health, Hello-World with a byte-identical GET, and all 15 conformance cases were checked against it from Chrome. Sleep when idle (Serverless) is still off, waiting for Kaan.

**Spec:** docs/Models/v1/v1.1/spec-v1.1.md, user stories 9, 55, 56

- [x] The image builds locally, includes git and holds no credentials. Its run store location is writable.
- [x] The container serves only the v1 app; v0's webhook routes can't be reached.
- [x] Run locally, the container answers health and analyses octocat/Hello-World at 7fd1a60 through the default remote base URL.
- [x] With the container held to 512 MB, two simultaneous analyses of a small public repo both finish.
- [ ] Once Kaan approves the push and the Railway setup, the service answers health at its public URL within about a minute of waking. A POST for Hello-World succeeds, and an immediate GET of its analysis_id returns the same bytes.
- [ ] The README gives the public URL (everything except the URL itself, which comes with the deploy) and names health as the warm-up call. It says the free service sleeps when idle and the first request can be slow. It also says run files are wiped on restart and redeploy, so a GET for an old run can return 404 on both teams' services and isn't a bug.
- [x] The whole suite is green, v0 included.
