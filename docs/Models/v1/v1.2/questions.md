# v1.2 · Questions to settle before building

**Before writing any v1.2 code, run `/grill-with-docs` on these questions with Kaan.** Record each answer in the [decision log](../../../plan/decisions-2026-10-17.md), and update CONTEXT.md and the models wherever an answer changes them.

These are the points where the code on the branch today (`kaan_v1` @ `501682b`) contradicts the roadmap or the models, or would break a test once v1.2 lands.

1. **`Source/LLM_Shell/llm.py` can't be imported.** It imports `IssueType`, and `schemas.py` has none. Where does the drift check live: in `LLM_Shell/` as it is now, or in `GitHub_Connector/`, the only package the course coverage report counts? Also tell Muhammad, whose code it is.
2. **Enum or string for `issue_type`?** `llm.py` expects an `IssueType` enum. `Finding.issue_type` is a plain `str`, copied from the pod, and putting an enum there changes `/system/openapi.json`, which fails the schema conformance test.
3. **What form does `finding_id` take?** `llm.py` uses a random uuid. M4 says to use a hash of `issue_type`, `code_file` and `documentation_file`, so repeat runs give the same id (AC-10), and to ask the pod first, because the field is shared.
4. **How are docs over the budget listed?** CONTEXT.md, M3 and M4 say every path in `skipped[]` is also in `changes[]`. Docs over the budget can be files that didn't change, so which rule gives way? And is the reason the code `OVER_DOC_BUDGET` (T12-Q7)?
5. **Does the 120 s deadline cover the model call?** The roadmap (slice 3) and M2 say the deadline covers the whole analysis, but today only the git calls enforce it.
6. **How do tests and conformance cope with a probabilistic model?** `tests/reference.py` compares `issues[]` exactly, but the roadmap's v1.2 criteria ask only for a shape check. And without a `GEMINI_API_KEY`, every existing test that analyses a repo with both code and docs would get 500 `LLM_UNAVAILABLE`.
