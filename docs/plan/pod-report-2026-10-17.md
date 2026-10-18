# Report to the pod: conformance run, 2026-10-17

A draft for Kaan to send. It lists what our conformance test found in the reference service (https://doc-tracker-5t4s.onrender.com/system), and the questions we still need the pod to answer. The details are in [decisions-2026-10-17.md](decisions-2026-10-17.md).

## Faults we found

1. **Doc files come back as OTHER, so T-04 fails.** `docs/**`, `*.md`, `*.rst` and `*.txt` are OTHER on your service, and the category enum has no DOCUMENTATION. M0's T-04 expects DOCUMENTATION. Ours returns it (roadmap decision 2).
2. **A setup with no body names no field.** `POST /system/test/setup` with no body, or with a JSON `null` body, answers 400 `{"message": " is required", "source": "system"}`, with nothing before "is". Ours says "body is required" (T12-Q4).

## Questions

1. **Which file types do you skip?** We've seen `UNSUPPORTED_FILE_TYPE` for `.lock`, `.png`, `.svg`, `.ai` and `.html`, and for symlinks and submodules. Can you send the full list, and do you ever skip a file because of its content (binary, too large or not UTF-8)? (T12-Q2)
2. **How do you classify `run.sh`?** Your service said IMPLEMENTATION. Is that because of the `.sh` extension or the executable bit? (T12-Q11)
3. **What answers an unexpected git failure?** When git fails for a reason other than a timeout, a missing repository or an unknown commit, which status code and error code do you return?
4. **Can you confirm the `/test` semantics?** We read the report as counting the executable lines of your package that ran on any request since the session's setup, whichever session the request named.

## Differences we keep on purpose

Not faults on your side, listed so you know why our output differs: hidden paths (any segment starting with `.`) are left out of ours (T12-Q9); our extra skip codes `BINARY_FILE`, `FILE_TOO_LARGE` and `NOT_UTF8` (T12-Q2); a short SHA that can't be fetched asks for the full 40 characters (Q6); `config_version` hashes our own rules; `tool_version` ends with the build, as in `1.1.0+abcdef0` (T12-Q5).
