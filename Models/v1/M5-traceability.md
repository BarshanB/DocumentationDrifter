# M5 · Requirement traceability

**Question:** Which v1 model carries each Phase 2 requirement, and which automated check holds it?

```mermaid
flowchart LR
  accTitle: M5 requirement traceability
  accDescr: Five requirements are realized in v1 through models M1 to M4 and held by automated checks. REQ-02 and REQ-03 are dashed because they are not implemented in Phase 3; they are deferred to v2 and v3. The v3 box also lists AC-06 with durable runs, which finishes REQ-04.

  subgraph REQS["Phase 2 requirements"]
    R1["REQ-01 · detect changes and category"]
    R4["REQ-04 · keep traceable evidence"]
    R5["REQ-05 · explicit errors"]
    R6["REQ-06 · read-only, no execution"]
    R7["REQ-07 · consistent, testable results"]
    R2["REQ-02 · flag missing or outdated docs"]
    R3["REQ-03 · human review"]
  end

  subgraph CHECKS["Automated checks in v1"]
    C1["AC-01 · T-01 to T-04, T-06, T-07<br/>connector tests 1-8, 10, 11"]
    C4["AC-06 · T-05"]
    C5["AC-07 · AC-08 · test 12"]
    C6["AC-09 · test 9 · test 12"]
    C7["AC-10 · conformance test"]
  end

  subgraph LATER["Dashed · not implemented in Phase 3"]
    V2["v2, Phase 4<br/>AC-02 · AC-03 · AC-10"]
    V3["v3, Phase 5<br/>AC-04 · AC-05 · AC-09 · AC-10<br/>AC-06 durable, finishes REQ-04"]
  end

  R1 -->|"M1 connector · M3 rules"| C1
  R4 -->|"M2 SAVING · M4 run file"| C4
  R5 -->|"M2 final states · M4 ErrorBody"| C5
  R6 -->|"M1 boundary · M2 RESOLVING"| C6
  R7 -->|"M4 schema · sorted lists"| C7
  R2 -.->|"issues[] stays empty"| V2
  R3 -.->|"no findings to review yet"| V3

  classDef later stroke-dasharray: 5 5,color:#666
  class R2,R3,V2,V3 later
  style LATER stroke-dasharray: 5 5
```

**Dashed boxes and arrows are not implemented in Phase 3.** REQ-02 is closed in v2 (Phase 4) and REQ-03 in v3 (Phase 5). REQ-04 is held in v1 while the service stays up, and is fully closed in v3, when runs survive a redeploy and an idle spin-down.

- **Representation.** Each requirement points to the models that realize it, and each edge ends at the check that would fail if the realization broke.
- **Property.** All seven requirements are accounted for. Five are held by automated checks in v1, and two are explicitly deferred, with the version and acceptance criteria that will close them. REQ-04 is held in v1 and finished in v3.
- **Checked by.** This model is itself the checklist for the v1 demo: every solid edge must have a passing check before v1 is called done. AC-10 is checked without its confidence clause, since the contract has no confidence field.
