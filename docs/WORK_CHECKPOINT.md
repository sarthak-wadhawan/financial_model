# UX overhaul — portable checkpoint

- Branch: `work/trading-copilot-ux` (never merge until final gates pass).
- Base commit: `1f81b0041313cfb5f7a3ac519e3e1a7f38ca1e22` (verified R1). Checkpoint commit: use `git log -1 --format=%H -- docs/WORK_CHECKPOINT.md`; a commit cannot embed its own hash.
- Completed: recovery and bounded UX DAG planning only. Existing A–P/R1 history preserved.
- Incomplete: UX1–UX9 below; no new product completion claim.
- Baseline evidence: R1 532 backend passed/35 skipped, 163 frontend unit, 15 startup, 122 browser; historical, not rerun for this overhaul.
- Known gaps: minimal hidden chart, generic insider rendering, incomplete identity/earnings coverage, split calendars, unexplained quant scores, dense stock sections, unwired sidebar collapse. External BLS/news limitations remain.
- Current subagents: read-only exploration complete; none editing.
- Next action: implement UX1 shell and UX2 source/contract investigation independently (at most two agents); independent review before marking a node complete.
- Resume: `git fetch origin && git switch work/trading-copilot-ux && git pull --ff-only origin work/trading-copilot-ux`; read this document and final UX section of `docs/current_task_graph.md`. Preserve local changes before switching. Normal app: `npm --prefix frontend run dev` (Node22; installs per START_HERE).
- Publication: this initial checkpoint must be pushed before implementation. Verify with `git ls-remote origin refs/heads/work/trading-copilot-ux` matching local HEAD. Subsequent checkpoint commits follow each completed node.
- Private/local state excluded: original database, `.env`, generated artifacts, unrelated user scripts and untracked skills. These are not required to clone source; supply local credentials privately. Do not copy databases/secrets to Git.
- Scope: Phase≤11 website only; zero-LLM, human decisions, no trading/retraining/Phase12. Model A repository not found at the requested path; no validated predictions assumed.
