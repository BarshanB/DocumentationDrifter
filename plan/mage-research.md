# MAGE modeling: what the v1 models follow

Notes for the [v1 models](../Models/v1/README.md), written 2026-10-17. Every claim below comes from the MAGE source repository, `github.com/davisjam/model-based-agentic-software-engineering` (the source of the book linked in the course), at its default branch on that date. Paths are relative to that repo.

## How MAGE says to model

- **Start from one engineering question, then pick the smallest representation that answers it.** "Choose the engineering question first", and "the goal is not to model the whole system" (`plugin/mage/skills/self-governance/modeling/repertoire.md`; book front matter). In practice, each v1 model opens with its question.
- **A model is a purposeful reduction.** "Preserve the distinctions needed to answer the question; omit distinctions that do not contribute to it" (`book/part2/2.6-modeling-summary.md`, item 1).
- **Six model classes, each defined by the question it answers.** Structural (what exists, how parts relate), behavioral (what may happen, in what order), ownership, decision (what is allowed, which choice), measurement and provenance (what happened, what evidence). The classes may overlap (book Fig. 0.4-1). v1 uses structural (M1, M4), behavioral (M2), decision (M3) and provenance (M4, M5). Ownership and measurement have no v1 question: there are no concurrent workers, and the only bounds, the 1 MB cap and the git timeouts, appear as guards in M2 and M3.
- **Every model answers four questions:** engineering question, representation, property, and enforcement and correspondence (`book/appendix-models/_opening.md`). The v1 files use Question, Representation, Property and Checked by.
- **Link models through shared identity and traceability** (book Fig. 0.4-1, §2.5). The v1 models share terms from `CONTEXT.md`, cross-reference each other (M1 → M3, M2 → M4), and M5 ties every requirement to a model and a check.
- **Maintain the correspondences you depend on.** "Check correspondence" and "derive the obligation set" are named moves (`plugin/mage/skills/self-governance/modeling/moves.md`, moves 3 and 4). In v1 the tests are the correspondence checks, and M5 is the obligation set.

## How MAGE says to draw

From `plugin/mage/skills/self-communicate/drawing/diagrams.md`:

- **Mermaid first.** The diagram is text in the same Markdown file as its prose, so it is reviewed and diffed like code. Hand-drawn SVG is only for layouts Mermaid can't express.
- **Less is more.** "Pick the simplest type that carries the shape", strip decoration, and split a crowded diagram rather than add to it.
- **Match the type to the shape:** a context or component diagram for structure, a state diagram for a lifecycle, a flowchart for decision logic, and an ER diagram for a schema.
- **Generate pictures from the model, don't keep a hand-drawn second copy.** That is why the PNGs in `Models/v1/rendered/` are regenerated from the Mermaid blocks.
- **Accessibility.** Each diagram carries `accTitle` and `accDescr`, and no distinction relies on color alone. Parts not implemented in Phase 3 are dashed, not just grey, and labelled "not implemented in Phase 3".

## How this fits the course

The course's Phase 2 brief asks pods to "represent the specification using appropriate models" (state machines, schemas, interface definitions, workflows and so on), and the Phase 3–5 template asks for "updated system models as needed" with each delivery (`course/project/phase-2.md`, `course/project/phase-3-5.md`). The v1 models are that update for Phase 3. They narrow the pod's Phase 2 models M1 to M5 to what v1 builds.
