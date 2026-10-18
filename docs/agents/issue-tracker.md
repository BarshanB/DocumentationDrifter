# Issue tracker: Local Markdown

Issues for this repo live as markdown files in `.scratch/`. Specs and decisions live in `docs/plan/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/` (today: `.scratch/v1-1-change-detection/`)
- The spec is `docs/Models/<major>/<version>/spec-<version>.md` (today: `docs/Models/v1/v1.1/spec-v1.1.md`), and decisions go in `docs/plan/decisions.md` (a new session is a new dated section at its end), not in `.scratch/`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file
- Each ticket starts with these lines, in this order: `# NN: <title>`, `**What to build:**`, `**Blocked by:**`, `**Status:**`, `**Spec:**`, then its acceptance criteria as `- [ ]` checkboxes
- Triage state is recorded first on the `**Status:**` line, before any prose (e.g. `**Status:** ready-for-agent · decided on 2026-10-17`); see `triage-labels.md` for the role strings
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed). A spec goes to `docs/Models/<major>/<version>/spec-<version>.md` instead.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly (`16` means `.scratch/<feature-slug>/issues/16-*.md`).

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` (the Notes / Decisions-so-far / Fog body).
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
