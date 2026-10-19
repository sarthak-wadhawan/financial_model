---
name: plan-first-orchestrator
description: Plan complex engineering work before implementation and coordinate bounded subagents.
---

# Instructions

1. Inspect requirements, repository state, git status, tests, docs, and available skills first.
2. Do not edit code before producing a task DAG.
3. Define each node with:
   - objective
   - dependencies
   - owner/subagent
   - required skills
   - acceptance criteria
   - tests
4. Parallelize only independent nodes.
5. Delegate bounded work instead of performing everything in the primary context.
6. After each node: verify → repair if needed → update task graph.
7. Preserve results in repository artifacts, not long chat history.
8. Continue autonomously until a genuine blocker or success gate.