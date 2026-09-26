# Architecture

StockSense is one Odoo 18 addon, `stocksense`. All three areas live in this
project. Owners review changes to their area.

| Model | Purpose | Owner |
| --- | --- | --- |
| stocksense.product | Product with SKU, category, unit of measure | Member 1 |
| stocksense.product.category | Product category list | Member 1 |
| stocksense.warehouse | Warehouse with a unique code | Member 1 |
| stocksense.location | Location inside a warehouse | Member 1 |
| stocksense.stock | Balance per product and location | Member 1 |
| stocksense.stock.ledger | Immutable record of every stock change | Member 1 |
| stocksense.reorder.rule | Minimum and target per product and location | Member 1 |
| stocksense.inventory.service | The only code that changes stock (AbstractModel) | Member 1 |
| stocksense.operation | Receipt, delivery, transfer or adjustment header | Member 2 |
| stocksense.operation.line | Product and quantity on an operation | Member 2 |
| stocksense.dashboard | KPI and filter queries (AbstractModel) | Member 3 |
| stocksense.password.otp | Hashed one-time password reset codes | Member 3 |

## Inventory service contract

The service is an Odoo AbstractModel. Its methods are private (leading
underscore), so they cannot be called over RPC. Operations call it while
validating:

| Method | Used by | Effect |
| --- | --- | --- |
| `_get_stock(product, location)` | Everyone | Current quantity, 0 if no balance |
| `_lock_balances(operation)` | `action_validate` | Locks every affected product and location, in a fixed order |
| `_increase_stock(line, location)` | Receipt, transfer | Adds `line.quantity` |
| `_decrease_stock(line, location)` | Delivery, transfer | Subtracts `line.quantity`; fails on insufficient stock |
| `_move_stock(line, source, destination)` | Transfer | Decrease at the source, then increase at the destination |
| `_adjust_stock(line, location)` | Adjustment | Sets stock to `line.counted_quantity` |

`_increase_stock`, `_decrease_stock` and `_adjust_stock` each write one ledger row that links to the operation and line. `_move_stock` writes two, one at the source and one at the destination. The
service runs inside Odoo's current transaction and never commits. Operations
never write stock or ledger rows directly.

## Validation flow

`stocksense.operation.action_validate()` runs inside a savepoint. It:

1. locks the operation row and checks that it is still open;
2. checks that the operation is complete (see [workflow.md](workflow.md));
3. locks the stock balances through the service;
4. calls `_apply_<type>(service)`, defined in `receipt.py`, `delivery.py`,
   `transfer.py` or `adjustment.py`;
5. sets the status to Done.

Any error rolls back every line. Concurrent validations wait on the locks.
If a serialization conflict occurs, Odoo retries the request.

## Authentication

- Sign-up uses Odoo's `auth_signup`. `res_users.py` copies the inactive
  `stocksense.signup_template_user`, an internal user whose home action is the
  dashboard. Invitations to existing contacts keep Odoo's portal template.
- `controllers/auth.py` extends Odoo's login controller so internal users land
  on the dashboard. It also serves the OTP pages at `/stocksense/reset_password`
  and `/stocksense/reset_password/verify`.
- Codes are 6 digits and HMAC-hashed with the database secret. They expire
  after 10 minutes and work once. A code locks after 5 wrong tries, and a new
  code can be sent at most once a minute. On a fresh install, Odoo's emailed reset
  link is turned off in favour of this flow. A database upgraded from an
  earlier version keeps its existing setting.

## Dashboard

`stocksense.dashboard.get_summary(filters)` returns the KPIs, recent
operations, low-stock items and filter options. Unknown filter values are
ignored. Warehouse, location and category narrow the KPIs. Document type and
status also narrow the operations list. It runs as the current user, so access
rights and company rules apply.
