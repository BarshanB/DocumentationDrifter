## Agent skills

### Issue tracker

Issues live as markdown files under `.scratch/<feature>/issues/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The five default roles, written first on each ticket's `**Status:**` line. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` at the root, decisions in `docs/plan/`. See `docs/agents/domain.md`.

### House rules

Comment format and the "simplest solution first" rule are in `Skills/CLAUDE.md`. The map of the docs is `docs/README.md`.

### Starting v1.2

Before writing any v1.2 code (the LLM drift check), run `/grill-with-docs` with the user on the questions in `docs/Models/v1/v1.2/questions.md`, one round at a time, and record the answers in the decision log. Don't build until every question there is answered.
