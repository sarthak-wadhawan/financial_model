---
name: backend-api-audit
description: Verify backend APIs, contracts, persistence, validation, error handling, and integration semantics.
---

# Instructions

For each relevant endpoint verify:
- expected status
- response schema
- semantic correctness
- bounds/filter behavior
- persistence
- validation
- error handling
- frontend contract compatibility

Test edge cases and failure states.

Do not accept HTTP 200 alone as correctness.

Add regression tests for discovered defects.

Return PASS / PARTIAL / FAIL.