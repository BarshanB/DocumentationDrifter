# v1 models

Five models of v1, the change detection API described in [plan/roadmap.md](../../plan/roadmap.md) and [plan/github-connector-steps.md](../../plan/github-connector-steps.md). They follow MAGE: each model starts from one engineering question and keeps only what that question needs. They narrow the Phase 2 models (M1 to M5 in [phase2.pdf](../../plan/phase2.pdf)) to what v1 actually builds, and they use the terms in [CONTEXT.md](../../CONTEXT.md).

v1 now ships in two steps (decision log, 2026-10-17): **v1.1** is the git change detection, and **v1.2** adds an LLM that decides drift and fills `issues[]`. Parts that only v1.2 has are labelled v1.2 in the diagrams.

| Model | MAGE class | Question |
|---|---|---|
| [M1 · Context and data flow](M1-context.md) | Structural | What is inside v1, what is outside it, and what data crosses the boundary? |
| [M2 · Analysis lifecycle](M2-lifecycle.md) | Behavioral | What can happen to one analysis request, and how does each path end? |
| [M3 · File rules](M3-file-rules.md) | Decision | For each changed path, is it reported, skipped or ignored, and which category does it get? |
| [M4 · Run file and API schema](M4-run-file.md) | Structural and provenance | What does a request carry, and what is saved and returned for each run? |
| [M5 · Requirement traceability](M5-traceability.md) | Provenance | Which v1 model carries each Phase 2 requirement, and which automated check holds it? |

## How to read them

Each file has the question, the diagram, and three lines: **Representation** (what the model contains), **Property** (what it lets you state precisely) and **Checked by** (the test that fails if the code stops matching the model).

- `REQ-0n` on an element means that element carries that Phase 2 requirement.
- **A dashed box or arrow is not implemented in Phase 3.** It belongs to v2 (Phase 4), v3 (Phase 5) or v4 and is drawn only so the boundary of what Phase 3 delivers is explicit. M1 and M5 group these parts under the heading "Dashed · not implemented in Phase 3", and M4 draws the v3 `Review` record dashed.
- `T-0n` are the shared tester's cases, `AC-nn` are the Phase 2 acceptance criteria, and "test n" is the numbered connector test list in the roadmap's v1 section.

## From boxes to files

All v1 code goes in `Source/GitHub_Connector/`, in new modules beside the v0 files (planned names, from the roadmap's v1 code layout):

| Model element | File |
|---|---|
| M1 API under /system | `api.py` (the app and routes) and `analysis.py` (`analyze()`) |
| M1 GitHub connector | `fetch.py` |
| M1 Classifier, M3 rules | `rules.py` and its rules file |
| M1 Run store | `runs.py` |
| M1 LLM drift check (v1.2) | a new module behind one function, provider and model in config (name not fixed yet) |
| M4 records | `schemas.py` |
| M1 Webhook receiver (dashed) | v0's `gitHook.py`, `parse.py`, `store.py`, `models.py` and `config.py`, which v1 neither serves nor imports |

## Source and pictures

The Mermaid block in each `.md` file is the model, and GitHub renders it inline. The PNG pictures in [rendered/](rendered/) are generated from those blocks, so after editing a block, regenerate its PNG instead of editing the picture by hand: run `mmdc` from `@mermaid-js/mermaid-cli` on the block with a `.png` output, or paste the block into mermaid.live and export a PNG.
