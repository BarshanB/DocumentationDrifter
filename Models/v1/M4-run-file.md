# M4 · Run file and API schema

**Question:** What does a request carry, and what is saved and returned for each run?

```mermaid
erDiagram
  accTitle: M4 run file and API schema
  accDescr: An AnalysisRequest either produces one AnalysisResult, which is saved as a run file, or is answered with an ErrorBody. A result holds lists of changes, skipped files and findings. Findings stay empty in v1. Review records, dashed, come in v3 and sit beside the run file without editing it.

  AnalysisRequest ||--o| AnalysisResult : "produces, saved as runs/id.json"
  AnalysisRequest ||--o| ErrorBody : "or is answered with"
  AnalysisResult ||--o{ Change : "changes[]"
  AnalysisResult ||--o{ Skipped : "skipped[]"
  AnalysisResult ||--o{ Finding : "issues[] (empty in v1)"
  Finding ||..o{ Review : "review records, v3 · run file never edited"

  AnalysisRequest {
    string repository "owner/name · required"
    string commit_id "7-40 hex · required"
    string base_commit "7-40 hex · optional"
  }
  AnalysisResult {
    string analysis_id "an- plus 32 hex"
    string repository "owner/name"
    string head_commit "40 hex"
    string base_commit "40 hex or null (first audit: root commit only)"
    string config_version "hash of all config: rules, plus mapping from v2"
    string tool_version "service version"
    enum status "SUCCESS in every saved v1 run"
    object error "null in every saved v1 run"
    string created_at "UTC, ms, Z"
  }
  Change {
    string path "repo-relative"
    string old_path "set for RENAMED and COPIED"
    enum change_type "ADDED MODIFIED DELETED RENAMED COPIED TYPE_CHANGED"
    enum category "IMPLEMENTATION DOCUMENTATION OTHER and 4 unused"
  }
  Skipped {
    string path "repo-relative"
    string reason "binary, too large or not UTF-8"
  }
  ErrorBody {
    string code "INVALID_REQUEST REPOSITORY_NOT_FOUND COMMIT_NOT_FOUND TIMEOUT WRITE_FAILED"
    string message "says what is wrong"
  }
  Finding {
    string finding_id "v2 · hash of issue_type, code_file, documentation_file"
    string issue_type "v2"
    string code_file "v2"
    string documentation_file "v2 · nullable"
    enum change_category "v2 · same enum as Change.category"
    string explanation "v2"
    enum verification_status "v2 · PENDING_REVIEW; reviews in v3"
  }
  Review {
    string analysis_id "v3 · the run reviewed"
    string finding_id "v3"
    enum decision "confirmed or dismissed, v3"
    string reviewer "v3"
    string decided_at "v3 · UTC"
  }

  classDef later stroke-dasharray: 5 5,color:#666
  class Review later
```

`Review` is shown for completeness but is not implemented in Phase 3. `Finding` is part of the v1 schema (slice 1), but `issues[]` is always empty until v2 (Phase 4), and review records come in v3 (Phase 5). The dashed line and box mark `Review`. Its shape still has to be agreed with the pod (roadmap decision 7).

`GET /system/analysis/{id}` always returns the run file's original bytes, so a reviewed finding still reads `PENDING_REVIEW` there; its current state lives in the `Review` records. `finding_id` is a hash of `issue_type`, `code_file` and `documentation_file`, so repeat runs give the same id (AC-10) and a review can carry over to later runs. Ask the pod what form theirs takes before v2, because the field is shared.

- **Representation.** Six records copied field for field from the pod's live OpenAPI, with one deliberate difference: DOCUMENTATION is added to the category enum, as Kaan decided. `Review` is a seventh record, ours until it is agreed with the pod.
- **Property.** One successful request produces one file, written once and never edited (REQ-04). All lists are sorted by path, so three runs on the same inputs differ only in `analysis_id` and `created_at` (REQ-07).
- **Checked by.** AC-06 (a separate JSON file with repo, commits, status and findings), AC-10 (repeat runs compare equal), and the conformance test, which expects differences only in `category` for doc files and in `config_version`.
