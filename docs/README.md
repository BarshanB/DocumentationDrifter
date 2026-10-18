# Docs

Specs and documentation for DocumentationDrifter. The glossary is [CONTEXT.md](../CONTEXT.md) at the repo root, and the tickets being worked on live in `.scratch/`.

## Read in this order

1. [CONTEXT.md](../CONTEXT.md): the words the project uses.
2. [plan/roadmap.md](plan/roadmap.md): the one plan, version by version (v1.1, v1.2, v2 and on).
3. The current version:
   - **v1.1 (built):** [plan/spec-v1.1.md](plan/spec-v1.1.md), with its tickets in `.scratch/v1-1-change-detection/`.
   - **v1.2 (not started):** settle [these questions](Models/v1/v1.2/questions.md) with `/grill-with-docs` before building.
4. [Models/v1/](Models/v1/README.md): the v1 models, M1 to M5, narrowed from the end product's M1 to M5.
5. [plan/decisions-2026-10-17.md](plan/decisions-2026-10-17.md): every decision with its reason. Decision 15 has its own page, [plan/new-branch-base.md](plan/new-branch-base.md).

## What each folder holds

| Folder | What it holds | Status |
|---|---|---|
| [endProduct/](endProduct/README.md) | The end product: the Phase 2 specification as text, its seven diagrams, the webhook-connector outline and schema v14 | Inspiration, not a blueprint |
| [plan/](plan/roadmap.md) | The roadmap, the version specs, the decision log and decision 15 | **Current.** Where these disagree with the end product, they win. |
| [plan/reports/](plan/reports/) | One-off reports: Actions readiness, the report to the pod, the MAGE research notes | Dated snapshots, not updated |
| [plan/history/](plan/history/) | The early build guides: the end-product plan, the commit fetcher plan, the connector steps | **Superseded** by the roadmap and the v1.1 spec, kept for their reasoning |
| [Models/](Models/v1/README.md) | The models of each version as it is built: v1 so far, with its v1.1 pictures and the v1.2 questions. Agents working on one area are meant to read the shared models plus the ones for that area. | Current |
| [agents/](agents/) | How the agent skills use this repo: issue tracker, triage labels, domain docs | Current |
