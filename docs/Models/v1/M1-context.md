# M1 · v1 context and data flow

**Question:** What is inside v1, what is outside it, and what data crosses the boundary?

```mermaid
flowchart LR
  accTitle: M1 v1 context and data flow
  accDescr: A client sends an AnalysisRequest to the v1 API, whose routes call analyze(). It asks the GitHub connector to clone the public repo read-only, the classifier turns changed paths into changes and skipped lists, and from v1.2 an LLM drift check sends the changed code and the doc files to an external LLM provider and fills issues. One run file is saved through the run store and returned. Dashed parts are not implemented in Phase 3: the GitHub Action reaches analyze() as a later caller, the mapping file arrives in v1.3 or v2, and review decisions go to separate review records.

  Client["Pod tester or any client<br/>T-01 … T-07"]

  subgraph V1["DocumentationDrifter service · v1 boundary"]
    API["API under /system<br/>routes call analyze()<br/>POST /analyze · GET /analysis/{id}<br/>REQ-05 · REQ-07"]
    CONN["GitHub connector<br/>git CLI · temporary clone<br/>REQ-01 · REQ-06"]
    CLS["Classifier<br/>path rules → category (M3)<br/>REQ-01"]
    LLM["LLM drift check · v1.2<br/>changed code + docs ≤ 200 KB → issues[]<br/>calls the LLM provider: Gemini free tier, set in config<br/>probabilistic until the final version<br/>REQ-02"]
    STORE[("Run store · save / load by id<br/>v1: local runs/{analysis_id}.json (M4)<br/>REQ-04")]
  end

  GH["GitHub public repo<br/>read-only · anonymous"]

  Client -->|"AnalysisRequest"| API
  API -->|"AnalysisResult or ErrorBody"| Client
  API -->|"repository · head · base"| CONN
  CONN -->|"clone and fetch only"| GH
  CONN -->|"changed paths · git letters"| CLS
  CLS -->|"changes[] · skipped[]"| API
  API -->|"changes · file contents"| LLM
  LLM -->|"issues[]"| API
  API -->|"write once"| STORE
  STORE -->|"read back unchanged"| API

  subgraph LATER["Dashed · not implemented in Phase 3"]
    ACT["GitHub Action · v3, Phase 5"]
    DET["Mapping file · v1.3 or v2"]
    REV["Human reviewers · v3, Phase 5"]
    REVREC["Review records · v3, Phase 5"]
  end

  ACT -.->|"POST /analyze · head · base"| API
  DET -.->|"narrows what the LLM reads"| LLM
  REV -.->|"review decisions"| REVREC
  REVREC -.->|"keyed by analysis_id"| STORE

  classDef later stroke-dasharray: 5 5,color:#666
  class ACT,DET,REV,REVREC later
  style LATER stroke-dasharray: 5 5
```

**Dashed boxes and arrows are not implemented in Phase 3.** They come in v1.3, v2 (Phase 4), v3 (Phase 5) or v4, and they are drawn only so the boundary of what Phase 3 delivers is explicit. The v0 webhook receiver was removed: the v3 GitHub Action covers the same events (roadmap decision 14).

- **Representation.** Five parts inside the boundary and one external system, plus the external LLM provider named inside the LLM drift check box. The drift check arrives in v1.2; v1.1 is the same picture without it. Each part names the requirement it carries. The routes only call `analyze()`, and the run store is reached only through `save` and `load` by `analysis_id`.
- **Property.** The only thing v1 does to the analysed repo is an anonymous clone and fetch into a temporary directory, so nothing in the repo is changed or executed (REQ-06). From v1.2, file contents leave the boundary only as the LLM prompt, and a failed LLM call fails the whole analysis rather than saving a run without findings. Every answer leaves through the API, and the run store is written once per successful analysis (REQ-04). Because the routes only wrap `analyze()`, a later caller reuses the same pipeline, and because storage sits behind `save` and `load`, v3 can make it durable by changing one module. Review decisions never edit a run file; they are separate records keyed by `analysis_id`.
- **Checked by.** AC-09 (the fixture repo hashes the same before and after), connector test 12 (a private repo is refused without credentials), and the conformance test against the pod's service.
