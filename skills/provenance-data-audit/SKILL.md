---
name: provenance-data-audit
description: Verify financial facts, evidence, source attribution, deduplication, and data-quality semantics.
---

# Instructions

Every material fact should preserve:
- source
- source URL/id
- publication/event time
- retrieval time
- evidence span where applicable
- confidence/verification state

Verify distinctions between:
- observed fact
- attributed statement
- deterministic derivation
- interpretation
- AI extraction

Check:
- consensus provenance
- amendments/revisions
- duplicate documents
- independently retrieved equivalent documents
- missing values remain missing

Return PASS / PARTIAL / FAIL.