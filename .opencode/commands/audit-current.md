# /audit-current — Read-Only Independent Audit Command

## Purpose

Perform a read-only independent audit of the current phase without implementing new work.

## Instructions

### 1. LOAD CONTEXT
- Read AGENTS.md
- Read docs/START_HERE.md
- Read docs/PROJECT_STATUS.md
- Read authoritative docs for current phase
- Inspect Git status/history

### 2. IDENTIFY CURRENT PHASE
- Read NEXT ACTION from START_HERE.md
- Confirm phase status in PROJECT_STATUS.md

### 3. RUN APPROPRIATE AUDITORS

#### Always Run:
- `@reviewer` — General independent audit

#### Conditionally Run:
- If external data/provider phase: `@provider-auditor`
- If security-relevant: `@security-reviewer`
- If research/model phase: `@research-auditor`

### 4. AGGREGATE FINDINGS
Collect all auditor outputs, classify overall:
- PASS — All auditors PASS
- PARTIAL PASS — Some PARTIAL PASS, no FAIL
- FAIL — Any FAIL

### 5. REPORT

Return structured report:

```
PHASE: [Phase name]
OVERALL: [PASS | PARTIAL PASS | FAIL]

REVIEWER: [PASS | PARTIAL PASS | FAIL]
  Findings: [...]
  Recommendations: [...]

PROVIDER AUDITOR: [PASS | PARTIAL PASS | FAIL | NOT APPLICABLE]
  Findings: [...]
  Recommendations: [...]

SECURITY REVIEWER: [PASS | PARTIAL PASS | FAIL | NOT APPLICABLE]
  Findings: [...]
  Recommendations: [...]

RESEARCH AUDITOR: [PASS | PARTIAL PASS | FAIL | NOT APPLICABLE]
  Findings: [...]
  Recommendations: [...]

OVERALL RECOMMENDATION:
- [Specific action 1]
- [Specific action 2]
...
```

### 6. DO NOT MODIFY
This is a READ-ONLY command. Do not change any code, tests, or documentation.

---

## Usage

Run when:
- User wants independent verification
- Before declaring a phase complete
- After implementing a fix to verify it's sufficient
- Periodic audit for regression detection