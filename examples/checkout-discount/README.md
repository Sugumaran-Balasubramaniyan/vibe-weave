# Checkout discount: pricing-rule mismatch

## Situation

Three agents implement a checkout promotion. They disagree about whether a customer can combine a coupon with a campaign discount.

```text
Frontend: show both discounts together
Pricing API: apply only the best discount
Tests: expect coupons and campaigns never to stack
```

## Why this is real-world important

This is not a code-style difference. It changes money charged to customers and can create support incidents.

## The question Weave should ask

**May coupon and promotion discounts stack?**

The chosen answer becomes the single pricing rule used by the UI, API, and tests. See [contracts.json](contracts.json).
