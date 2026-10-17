# M1 · v1 context and data flow

**Question:** What is inside v1, what is outside it, and what data crosses the boundary?

```mermaid
flowchart LR
  accTitle: M1 v1 context and data flow
  accDescr: A client sends an AnalysisRequest to the v1 API, whose routes call analyze(). It asks the GitHub connector to clone the public repo read-only, the classifier turns changed paths into changes and skipped lists, and one run file is saved through the run store and returned. Dashed parts are not implemented in Phase 3: the GitHub Action and the webhook reach analyze() as later callers, and review decisions go to separate review records.

  Client["Pod tester or any client<br/>T-01 … T-07"]

  subgraph V1["DocumentationDrifter service · v1 boundary"]
    API["API under /system<br/>routes call analyze()<br/>POST /analyze · GET /analysis/{id}<br/>REQ-05 · REQ-07"]
    CONN["GitHub connector<br/>git CLI · temporary clone<br/>REQ-01 · REQ-06"]
    CLS["Classifier<br/>path rules → category (M3)<br/>REQ-01"]
    STORE[("Run store · save / load by id<br/>v1: local runs/{analysis_id}.json (M4)<br/>REQ-04")]
  end

  GH["GitHub public repo<br/>read-only · anonymous"]

  Client -->|"AnalysisRequest"| API
  API -->|"AnalysisResult or ErrorBody"| Client
  API -->|"repository · head · base"| CONN
  CONN -->|"clone and fetch only"| GH
  CONN -->|"changed paths · git letters"| CLS
  CLS -->|"changes[] · skipped[]"| API
  API -->|"write once"| STORE
  STORE -->|"read back unchanged"| API

  subgraph LATER["Dashed · not implemented in Phase 3"]
    ACT["GitHub Action · v3, Phase 5"]
    HOOK["Webhook receiver · built in v0, wired in v4"]
    DET["Mapping and detector · v2, Phase 4"]
    REV["Human reviewers · v3, Phase 5"]
    REVREC["Review records · v3, Phase 5"]
  end

  ACT -.->|"POST /analyze · head · base"| API
  HOOK -.->|"calls analyze()"| API
  DET -.->|"adds issues[]"| API
  REV -.->|"review decisions"| REVREC
  REVREC -.->|"keyed by analysis_id"| STORE

  classDef later stroke-dasharray: 5 5,color:#666
  class ACT,HOOK,DET,REV,REVREC later
  style LATER stroke-dasharray: 5 5
```

**Dashed boxes and arrows are not implemented in Phase 3.** They come in v2 (Phase 4), v3 (Phase 5) or v4, and they are drawn only so the boundary of what Phase 3 delivers is explicit. The webhook is wired only in v4, because the v3 GitHub Action covers the same events (roadmap decision 14).

- **Representation.** Four parts inside the boundary and one external system. Each part names the requirement it carries. The routes only call `analyze()`, and the run store is reached only through `save` and `load` by `analysis_id`.
- **Property.** The only thing v1 does to the analysed repo is an anonymous clone and fetch into a temporary directory, so nothing in the repo is changed or executed (REQ-06). Every answer leaves through the API, and the run store is written once per successful analysis (REQ-04). Because the routes only wrap `analyze()`, a later caller reuses the same pipeline, and because storage sits behind `save` and `load`, v3 can make it durable by changing one module. Review decisions never edit a run file; they are separate records keyed by `analysis_id`.
- **Checked by.** AC-09 (the fixture repo hashes the same before and after), connector test 12 (a private repo is refused without credentials), and the conformance test against the pod's service.
