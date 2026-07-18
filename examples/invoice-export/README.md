# Invoice export: permission mismatch

## Situation

A team asks three agents to add “Export invoice”. Every agent sounds reasonable, but they interpret access differently.

```text
Frontend: show Export to every signed-in user
Backend:  allow Export only for admins
Tests:    expect non-admin requests to return 403
```

## What goes wrong without Weave

The UI can show a button that the API rejects. The test team may then weaken a test simply to make the branch green.

## What Weave does

1. Finds two values for `invoice_export.authorization`.
2. Asks: **Who may export invoices?**
3. Records `admin_only` as a shared Decision Contract.
4. Lets all three roles implement and prove the same behavior.

Open [contracts.json](contracts.json) to see the three Change Contracts.
