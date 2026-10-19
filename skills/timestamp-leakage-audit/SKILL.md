---
name: timestamp-leakage-audit
description: Detect fabricated timestamps and future-information leakage in financial pipelines and backtests.
---

# Instructions

Distinguish explicitly:
- event_date
- scheduled_at
- announcement_released_at
- filing_accepted_at
- published_at
- first_seen_at
- retrieved_at
- consensus_as_of
- market timestamp
- calculation timestamp

Verify:
- BMO/AMC are session semantics
- unknown time stays unknown
- no midnight fabrication
- no future bars
- no revised values leaking backward
- historical state reflects only information available then

Add leakage regression tests.

Return PASS / PARTIAL / FAIL.