# Operation workflow

```text
Draft ──Confirm──▶ Waiting ──Mark Ready / Picked & Packed──▶ Ready
  │                   │                                        │
  └──────────────── Validate (posts stock) ───────────────────┴──▶ Done
Draft / Waiting / Ready ──Cancel──▶ Canceled ──Reset to Draft──▶ Draft
```

- Only Draft operations can be edited. Waiting, Ready and Canceled operations
  can be reset to Draft.
- Waiting and Ready track progress. They do not reserve stock. Availability
  is checked when you validate.
- Done operations are final. To correct one, create a new operation or an
  adjustment.

## What each type needs and does

| Type | Needs | On validate |
| --- | --- | --- |
| Receipt | Supplier and destination location | Stock +quantity at the destination |
| Delivery | Source location | Stock −quantity at the source. Blocked if stock is insufficient |
| Internal transfer | Source and destination, which must differ | −quantity at the source, +quantity at the destination; total unchanged |
| Adjustment | The counted location, in the Destination Location field, with each product once | Stock at that location set to the counted quantity; the difference is logged |

Every operation needs at least one line. Archived products cannot be moved.

## Example: the problem statement flow

1. Receive 100 kg steel into Main Store: Main Store has 100.
2. Transfer 100 kg from Main Store to Production Rack: Main Store has 0 and
   Production Rack has 100, so the total is still 100.
3. Deliver 20 kg from Production Rack: Production Rack has 80.
4. Count 77 kg at Production Rack after 3 kg is damaged: the adjustment logs
   −3, and Production Rack has 77.

Each step appears in Move History.

## Tests

`tests/test_operations.py` covers each type's quantities and ledger rows,
insufficient stock, multi-line rollback, double validation, protection of
completed and canceled operations, invalid quantities and locations, forged
status values, copying and company isolation. A separate concurrency check
covers simultaneous validation.
