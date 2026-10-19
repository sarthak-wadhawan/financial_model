---
name: deployment-readiness-audit
description: Assess whether the architecture can later run in managed cloud infrastructure without the developer computer.
---

# Instructions

Verify separation:

Browser
→ API
→ server-side providers/database/models

Check readiness for:
- static frontend hosting
- managed backend
- managed database
- scheduled jobs
- alert workers
- secret management
- provider credentials
- persistent storage
- observability

Do not deploy unless explicitly assigned.

Document blockers and required Phase 14 work.

Return PASS / PARTIAL / FAIL.