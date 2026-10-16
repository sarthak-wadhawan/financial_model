# UX overhaul — portable checkpoint

- Branch: `work/trading-copilot-ux` (never merge until final gates pass).
- Base commit: `1f81b0041313cfb5f7a3ac519e3e1a7f38ca1e22` (verified R1). Checkpoint commit: use `git log -1 --format=%H -- docs/WORK_CHECKPOINT.md`; a commit cannot embed its own hash.
- Completed: recovery and bounded UX DAG planning, pushed at `9d5cad96f57c36ded4d6982c06fb5a46e81612b2` and remote SHA verified. Existing A–P/R1 history preserved.
- Incomplete: UX1–UX9 below; no new product completion claim.
- Baseline evidence: R1 532 backend passed/35 skipped, 163 frontend unit, 15 startup, 122 browser; historical, not rerun for this overhaul.
- Known gaps: minimal hidden chart, generic insider rendering, incomplete identity/earnings coverage, split calendars, unexplained quant scores, dense stock sections, unwired sidebar collapse. External BLS/news limitations remain.
- Current subagents: UX1 BUILD `ses_eb9e882c0ffe7Y42HQBjcqFyLz` owns App/layout/styles/tests; UX2 source audit `ses_eb9e85e36ffeNyvGuc1mR01zwB` owns only `UX_DATA_CONTRACT_AUDIT.md`. Agent sessions are machine-local; resume from committed files/contracts, not those IDs.
- Next action: consume UX1/UX2 results, run affected checks, request independent review before marking either complete; then implement UX2 contract fixes and UX3 stock/chart. Never assume in-flight local agent output is committed.
- Resume: `git fetch origin && git switch work/trading-copilot-ux && git pull --ff-only origin work/trading-copilot-ux`; read this document and final UX section of `docs/current_task_graph.md`. Preserve local changes before switching. Normal app: `npm --prefix frontend run dev` (Node22; installs per START_HERE).
- Publication: initial checkpoint was pushed before implementation and remote matched. Verify latest with `git ls-remote origin refs/heads/work/trading-copilot-ux` matching local HEAD. Subsequent checkpoint commits follow each completed node.
- Private/local state excluded: original database, `.env`, generated artifacts, unrelated user scripts and untracked skills. These are not required to clone source; supply local credentials privately. Do not copy databases/secrets to Git.
- Scope: Phase≤11 website only; zero-LLM, human decisions, no trading/retraining/Phase12. Model A repository not found at the requested path; no validated predictions assumed.
- Fresh baseline spot checks: four settings/snapshot backend tests passed; actual Chromium TMO page, proxied JSON health and TMO search returned200 with zero uncaught errors. This is not a new broad regression or overhaul PASS. Normal3000/8000 remains running.
- Documentation gap: referenced `docs/MODEL_AND_DEPLOYMENT_ARCHITECTURE.md` is absent from the checked-out repository. Do not invent its contents; follow the available approved architecture and explicit ModelA/zero-LLM constraints.
