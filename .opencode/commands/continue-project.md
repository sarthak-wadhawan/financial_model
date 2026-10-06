# /continue-project — Autonomous Development Command

## Purpose

Execute the full autonomous development cycle for the current approved phase.

## Instructions for Shepherd

Execute the following steps IN ORDER:

### 1. RECONSTRUCT STATE
- Read AGENTS.md
- Read docs/START_HERE.md
- Read docs/PROJECT_STATUS.md
- Read authoritative docs for current phase (from DEVELOPMENT_ROADMAP_UPDATED.md)
- Inspect Git status, recent commits, working tree

### 2. VERIFY BASELINE
- Run `python3 -m pytest -q` (offline tests)
- Verify all tests pass
- Compare documented state vs actual code

### 3. DETERMINE CURRENT PHASE
- Read NEXT ACTION from START_HERE.md
- Confirm phase status in PROJECT_STATUS.md
- Identify if phase is: NOT_STARTED | IN_PROGRESS | NEEDS_REVIEW | NEEDS_FIX | READY_FOR_NEXT

### 4. CREATE PHASE GRAPH
- Decompose phase into task nodes (DAG)
- Identify dependencies
- Determine which nodes can run in parallel (true independence only)
- Assign bounded tasks to appropriate agents/subagents
- Use worktrees for materially competing experiments only

### 5. DELEGATE & EXECUTE
- Launch independent task agents in parallel where safe (true independence only)
- Use specialist agents for bounded work
- Communicate through artifacts/interfaces, not chat
- Give agents ONLY: task, interfaces, relevant files, requirements, tests, output contract
- Use cheap/free models for routine work, strong models for architecture/ambiguity
- Preserve only compact results: STATUS, FILES, INTERFACE, TESTS, FINDINGS, BLOCKERS

### 6. MERGE & INTEGRATION TEST
- Collect results from completed nodes
- Run integration tests
- Check for regressions

### 7. INDEPENDENT REVIEW (MANDATORY)
- Invoke `@reviewer` for current phase audit
- If provider/data phase: also invoke `@provider-auditor`
- If security-relevant: also invoke `@security-reviewer`
- If research/model phase: also invoke `@research-auditor`
- Collect all findings

### 8. FIX & RETEST
- Address ALL FAIL/PARTIAL findings
- Rerun only affected tests/nodes
- Repeat review until PASS

### 8. REGRESSION TEST
- Run FULL test suite: `python3 -m pytest -q`
- If live tests relevant: `RUN_LIVE_TESTS=1 python3 -m pytest -q`
- All tests must pass

### 9. DOCUMENT
- Update docs/START_HERE.md (CURRENT PHASE, WHAT WORKS, LIMITATIONS, TEST STATUS, NEXT ACTION)
- Update docs/PROJECT_STATUS.md (test results, dev history, limitations)

### 10. COMMIT & PUSH
- git status
- git diff
- git add -A
- git commit -m "Phase X complete: [summary]"
- git push origin main

### 11. UPDATE NEXT ACTION
- Update NEXT ACTION in START_HERE.md
- Update docs/DEVELOPMENT_ROADMAP_UPDATED.md if needed
- Continue to next approved phase automatically

---

## Abort Conditions

Stop and report to user if:
- Paid service required
- Missing credential that cannot be avoided
- Destructive operation
- Force push/history rewrite needed
- Live trading/account action
- Major conflict with approved product requirements
- Genuine external blocker

---

## Token Efficiency Rules

- Give each agent ONLY: task, interfaces, relevant files, requirements, tests, output contract
- Use repository files as shared memory, not chat context
- Require short structured outputs from subagents
- Discard intermediate reasoning after task completion
- Use cheap models for routine work, strong models for architecture/ambiguity

---

## Output

Return final status:
```
PHASE: [Phase name]
STATUS: [PASS | BLOCKED]
FILES CHANGED: [...]
TESTS: [count passed / skipped]
NEXT PHASE: [name]
```