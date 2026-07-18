# Learn Vibe Weave through examples

Each folder is a tiny product scenario. Start with the `README.md`, then open `contracts.json` to see the exact information that Vibe Weave compares.

| Example | The hidden disagreement | The one question Weave asks |
| --- | --- | --- |
| [Invoice export](invoice-export) | Who is allowed to export an invoice? | Who may export invoices? |
| [Checkout discount](checkout-discount) | Can a coupon stack with a promotion? | May coupon and promotion discounts stack? |
| [Database migration](database-migration) | Is a destructive migration allowed in production? | May this migration drop production data? |

## How to read a contract

```json
{
  "role": "backend",
  "files": ["api/invoices.py"],
  "decisions": {"invoice_export.authorization": "admin_only"},
  "public_contracts": ["GET /invoices/{id}/export"],
  "proofs": ["non-admin request returns 403"]
}
```

- `role`: who is doing this part of the work.
- `files`: where that role expects to edit.
- `decisions`: meanings that must match across roles.
- `public_contracts`: interfaces other work depends on.
- `proofs`: the evidence the role promises to return.

You do not need to memorize this format. The important idea is simple: **make the assumptions visible before parallel edits begin.**
