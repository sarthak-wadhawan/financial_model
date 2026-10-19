---
name: documentation-reconciliation
description: Reconcile project documentation against verified implementation and remove stale claims.
---

# Instructions

Compare:
- requirements
- architecture
- roadmap
- START_HERE
- PROJECT_STATUS
- audit reports
- actual code/tests/git state

Code and verified behavior take precedence over stale documentation.

Remove contradictions such as simultaneous IN PROGRESS / COMPLETE states.

Update:
- current status
- test counts
- known limitations
- exact next action

Do not change working code merely to match old docs.