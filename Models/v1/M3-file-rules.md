# M3 · File rules

**Question:** For each changed path, is it reported, skipped or ignored, and which category does it get?

```mermaid
flowchart TD
  accTitle: M3 file rules
  accDescr: Each changed path is ignored if it is hidden or not a regular file, skipped if it is binary, over 1 MB or not UTF-8, and otherwise reported in changes with a category from the first matching rule.

  P(["Changed path from git diff --name-status -M base head"])
  P --> H{"Any segment starts with a dot?"}
  H -->|"yes"| IGN["Ignored · not listed anywhere"]
  H -->|"no"| M{"Regular file at head?<br/>base if DELETED<br/>mode 100644 or 100755"}
  M -->|"no · symlink or submodule"| IGN
  M -->|"yes"| B{"Binary, over 1 MB,<br/>or not UTF-8?"}
  B -->|"yes"| SK["skipped[] with a reason · REQ-05"]
  B -->|"no"| R1{"requirements*.txt?"}
  R1 -->|"yes"| OTH["OTHER"]
  R1 -->|"no"| R2{"docs/** · *.md · *.rst · *.txt?"}
  R2 -->|"yes"| DOC["DOCUMENTATION"]
  R2 -->|"no"| R3{"src/** · tests/** · *.py?"}
  R3 -->|"yes"| IMP["IMPLEMENTATION"]
  R3 -->|"no"| OTH
  DOC --> CH["changes[] entry · REQ-01"]
  IMP --> CH
  OTH --> CH
```

Each entry in `changes[]` also carries a `change_type` taken from git's status letter:

| git letter | `change_type` | `old_path` |
|---|---|---|
| A | ADDED | null |
| M | MODIFIED | null |
| D | DELETED | null |
| R | RENAMED | the old path |
| C | COPIED | the source path |
| T | TYPE_CHANGED | null |

A first audit (a root commit, so no base) diffs against the empty tree, so every path is ADDED.

**Side.** The mode, size, binary and UTF-8 checks read the head side of each path, or the base side for DELETED. So a symlink that becomes a regular file is reported as TYPE_CHANGED, and a regular file that becomes a symlink is ignored; the conformance test checks this against the pod. The size and binary checks run only on changed paths, after `git diff --numstat` has fetched their blobs in one batch.

- **Representation.** Three admission checks and one ordered list of category rules, where the first match wins. The rules live in one config file. `config_version` is a short hash of every config input that affects the output: the rules file in v1, plus the mapping file at head from v2.
- **Property.** Every changed path ends in exactly one place: ignored, `skipped[]` or `changes[]`. Nothing that wasn't checked is reported as checked (REQ-05). DESIGN, ARCHITECTURE, SPECIFICATION and REQUIREMENT have no rules in v1, so those files fall to DOCUMENTATION under `docs/` or when named `*.md`, `*.rst` or `*.txt`, and to OTHER otherwise.
- **Checked by.** T-04 (`docs/installation.rst` → DOCUMENTATION), connector tests 2, 3, 10 and 11 (added and deleted files, rename, hidden files, symlink and binary), and T-03 (a rename is one change).
