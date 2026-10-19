---
name: test-generation
description: Create targeted permanent regression tests from requirements and discovered defects.
---

# Instructions

Before writing tests:
1. Identify behavior contract.
2. Identify failure modes.
3. Check existing coverage.

Create the smallest useful tests covering:
- happy path
- boundary cases
- missing data
- invalid input
- provider failure
- regression case

Never weaken a failing test merely to obtain PASS.

Prefer deterministic fixtures.

Report tests added and commands used.