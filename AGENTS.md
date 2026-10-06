# Trading Copilot — OpenCode Project Instructions

This file is automatically loaded by OpenCode as permanent project guidance.

## Core Directives

**Every OpenCode session MUST:**
1. Read `docs/START_HERE.md` first
2. Treat documented completed phases as completed but verify reality against code/tests
3. Follow the approved roadmap in `docs/DEVELOPMENT_ROADMAP_UPDATED.md`
4. Use interpretation + impact as the core product philosophy
5. Maintain zero-LLM operation (`LLM_ENABLED=false` by default)
6. Keep Model A separate from Trading Copilot
7. Preserve evidence/provenance for all data
8. Preserve historical/revision data for research
9. Never fabricate missing information
10. Keep company impact separate from stock impact
11. Preserve Phase 9 as the interpretation layer
12. Use autonomous competing experiments for model research
13. Run tests before declaring success
14. Update `docs/START_HERE.md` and `docs/PROJECT_STATUS.md`
15. Commit/push only after successful verification
16. Never force-push
17. Never make live trades
18. Never initiate paid services
19. Never expose credentials
20. Stop only for genuine autonomy-boundary issues

## Autonomy Boundaries — Ask User Only For:
- Paid service required
- Missing credential that cannot be avoided
- Destructive operation
- Force push/history rewrite
- Live trading/account action
- Major conflict with approved product requirements
- Genuine external blocker

Do NOT ask routine engineering questions.

## Reference Documents (authoritative):
- `docs/FINAL_PRODUCT_REQUIREMENTS.md` — what the finished product must do
- `docs/SYSTEM_ARCHITECTURE_UPDATED.md` — approved architecture
- `docs/DEVELOPMENT_ROADMAP_UPDATED.md` — build sequence and phase success criteria
- `docs/MODEL_AND_DEPLOYMENT_ARCHITECTURE.md` — model research, LLM policy, browser/serverless deployment
- `docs/PROJECT_STATUS.md` — detailed implementation history/current factual state
- `docs/START_HERE.md` — concise current-session bootstrap/handoff

## Orchestration Commands
- `/continue-project` — Continue autonomous development
- `/audit-current` — Read-only independent audit of current phase

## Graph Engineering & Token Efficiency

**Graph Engineering — Shepherd = Orchestrator:**
- Decompose phases into task graphs (DAG)
- Run independent nodes in parallel
- Merge results, then independent review
- Fix only failed nodes, not entire phase

**Shepherd = Orchestrator, NOT Primary Coder:**
- Understands phase, constructs task graph, assigns bounded work
- Specialist subagents perform implementation
- Shepherd owns architecture, subagents own bounded tasks

**Token Efficiency:**
- Give agents ONLY: task, interfaces, relevant files, requirements, tests, output contract
- Use repository files as shared memory, not chat context
- Require short structured outputs (STATUS, FILES, INTERFACE, TESTS, FINDINGS, BLOCKERS)
- Use cheap/free models for routine work, strong models for architecture/ambiguity
- Preserve only compact results after subtask completion

**Independent Review Node (Mandatory):**
Every meaningful phase graph ends with independent review node.
Reviewer must not blindly accept implementer's report.

**Provider Phase Graph:**
SOURCE AUDIT → IMPLEMENT → OFFLINE FIXTURES → LIVE GATED TEST → PROVIDER AUDITOR → INTEGRATION

**Model-Discovery Graph (Future):**
RESEARCH QUESTION → FROZEN CONTRACT → BASELINE/TREE/NEURAL (parallel) → INDEPENDENT EVALUATOR → LEAKAGE AUDITOR → LEADERBOARD → FOLLOW-UP

**Worktree Isolation:** For materially competing experiments (not trivial tasks)

**Observability:** Preserve lightweight graph/run summary per phase (nodes, deps, agent/model, duration, status, files, tests, retries)

**Optimize Orchestrator Over Time:** Learn from history, adjust parallelization, promote repeated audit checks to permanent tests