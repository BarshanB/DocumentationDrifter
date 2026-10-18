# M3 · File rules

**Question:** For each changed path, is it reported, skipped or ignored, and which category does it get?

Hidden paths are ignored. Every other changed path is reported in `changes[]`, and a path that can't be read as text is also listed in `skipped[]` with a reason code (decision log, T12-Q1, T12-Q2 and T12-Q9). A symlink or submodule is never read, so it is skipped as `UNSUPPORTED_FILE_TYPE`, except a switch to or from a regular file, which is one TYPE_CHANGED change and isn't skipped (T12-Q10, ticket 17).

```mermaid
flowchart TD
  accTitle: M3 file rules
  accDescr: Each changed path is ignored if it is hidden. Otherwise it is reported in changes with a category from the first matching rule. A symlink or submodule is also listed in skipped as UNSUPPORTED_FILE_TYPE unless it is a TYPE_CHANGED switch. A regular file is also listed in skipped with a reason code if its extension is on the denylist, or if it is binary, over 1 MB or not UTF-8. Each side of a rename is checked for hidden paths separately.

  P(["Changed path from git diff --name-status -M base head"])
  P --> H{"Any segment starts with a dot?"}
  H -->|"yes"| IGN["Ignored · not listed anywhere<br/>checked on each side of a rename"]
  H -->|"no"| M{"Regular file at head?<br/>base if DELETED<br/>mode 100644 or 100755"}
  M -->|"no · symlink or submodule"| R1
  M -->|"no, and also,<br/>unless TYPE_CHANGED"| SKU
  M -->|"yes"| R1{"requirements*.txt?"}
  M -->|"yes, and also"| U{"Extension on the denylist?<br/>.ai .html .lock .png .svg"}
  R1 -->|"yes"| OTH["OTHER"]
  R1 -->|"no"| R2{"docs/** · *.md · *.rst · *.txt?"}
  R2 -->|"yes"| DOC["DOCUMENTATION"]
  R2 -->|"no"| R3{"src/** · tests/** · *.py · *.sh?"}
  R3 -->|"yes"| IMP["IMPLEMENTATION"]
  R3 -->|"no"| OTH2["OTHER"]
  DOC --> CH["changes[] entry · REQ-01"]
  IMP --> CH
  OTH --> CH
  OTH2 --> CH
  U -->|"yes"| SKU["skipped[] · UNSUPPORTED_FILE_TYPE"]
  U -->|"no"| B{"Binary, over 1 MB,<br/>or not UTF-8?"}
  B -->|"yes"| SKC["skipped[] · BINARY_FILE,<br/>FILE_TOO_LARGE or NOT_UTF8 · REQ-05"]
  B -->|"no"| RD["readable as text, not skipped"]
```

Each entry in `changes[]` also carries a `change_type` taken from git's status letter:

| git letter | `change_type` | `old_path` |
|---|---|---|
| A | ADDED | null |
| M | MODIFIED | null |
| D | DELETED | null |
| R | RENAMED | the old path |
| C | COPIED | never produced: v1 runs `-M` only, so copies show as ADDED |
| T | TYPE_CHANGED | null |

A first audit (a root commit, so no base) diffs against the empty tree, so every path is ADDED.

**Hidden paths and renames.** The hidden-path check runs on each side of a rename. A rename out of a hidden path (`.github/a.md` → `docs/a.md`) is reported as ADDED with no `old_path`, and a rename into one (`docs/x.md` → `.archive/x.md`) as DELETED. A hidden path never appears anywhere, `old_path` included.

**Doc budget (v1.2).** The LLM is sent every DOCUMENTATION file at head, up to 200 KB in total (a config value). Docs past the budget go to `skipped[]` with the reason "over doc budget", so they are never reported as checked.

**Side.** The mode, size, binary and UTF-8 checks read the head side of each path, or the base side for DELETED. A switch between a regular file and a symlink or submodule is one TYPE_CHANGED change in either direction, and is not skipped; the conformance test checks this against the pod. Its content checks run only when the side checked is a regular file. The size and binary checks run only on changed paths, after `git diff --numstat` has fetched their blobs in one batch.

- **Representation.** Two admission checks, one ordered list of category rules where the first match wins, and a skip check: the extension denylist, then the binary, size and UTF-8 checks. The rules and the denylist live in one config file. `config_version` is a short hash of every config input that affects the output: the rules file in v1.1, plus the LLM provider, model and doc budget from v1.2, plus the mapping file at head once it lands in v1.3 or v2.
- **Property.** Every changed path is either ignored or in `changes[]`, and a path in `skipped[]` is always in `changes[]` too. Nothing that wasn't checked is reported as checked (REQ-05). The denylist and the content checks are the reference service's file-type rule plus our safety net; a file of a type the reference accepts that fails a content check is a known difference (T12-Q2). DESIGN, ARCHITECTURE, SPECIFICATION and REQUIREMENT have no rules in v1, so those files fall to DOCUMENTATION under `docs/` or when named `*.md`, `*.rst` or `*.txt`, and to OTHER otherwise.
- **Checked by.** T-04 (`docs/installation.rst` → DOCUMENTATION), connector tests 2, 3, 10 and 11 (added and deleted files, rename, hidden files, symlink and binary), the symlink and submodule tests in `tests/test_v1_changes.py` (ticket 17), and `tests/test_v1_skipped.py` (ticket 16), and T-03 (a rename is one change).
