# Database migration: rollout-safety mismatch

## Situation

Agents are asked to remove an obsolete customer column.

```text
Application agent: remove the column in this release
Database agent: keep the column for one compatibility release
Tests: expect old records to remain readable
```

## Why this matters

All three approaches can be valid. The dangerous part is shipping a mixture of them.

## The question Weave should ask

**May this migration drop production data now?**

With `no`, Weave can require a staged migration proof: dual-read compatibility first, removal later. See [contracts.json](contracts.json).
