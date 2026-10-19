---
name: repository-audit
description: Audit repository structure, implementation completeness, tests, git state, and stale artifacts.
---

# Instructions

Inspect:
- git status/log/diff
- source structure
- test structure
- configuration
- dependencies
- generated artifacts
- documentation

Verify:
- claimed features actually exist
- tests exercise them
- no abandoned partial implementations
- no duplicate/stale implementations
- working tree is understood

Return:
PASS / PARTIAL / FAIL
with material findings, affected files, and required repairs.