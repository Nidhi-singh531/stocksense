# Database design

Quantities use three decimal places. Every inventory and operation record
belongs to a company, and record rules hide other companies' data. Categories with no company are shared
across companies.

## Inventory

- **Product:** `name`, `sku` (unique per company), `category_id`,
  `unit_of_measure` (units, kg, liters, meters, boxes), `active`, `company_id`.
  The unit and company cannot change once the product is used in an operation.
  `initial_quantity` and `initial_location_id` are form-only inputs. On create,
  they post an adjustment.
- **Category:** `name` (unique within a company; shared categories with no
  company are not checked for duplicates), optional `company_id`.
- **Warehouse:** `name`, `code` (unique per company), `company_id`.
- **Location:** `name` (unique within its warehouse), `warehouse_id`. The
  company comes from the warehouse. A location used in operations cannot move
  to another warehouse.
- **Stock:** `product_id`, `location_id`, `quantity`. Unique per product and
  location, and the quantity can never be negative. Only the inventory service
  writes it.
- **Ledger:** `date`, `product_id`, `location_id`, `operation_id`,
  `operation_type`, `operation_line_id`, `quantity_before`, `quantity_change`,
  `quantity_after`, `user_id`. Created only by the service; it can never be
  edited or deleted.
- **Reorder rule:** `product_id`, `location_id` (unique pair),
  `minimum_quantity` and `target_quantity`, where 0 ≤ minimum ≤ target. The
  computed fields are `quantity_on_hand`, `suggested_quantity` and
  `below_minimum`, which is searchable.

## Operations

- **Operation:** `reference` (sequence `SS/<year>/<number>`),
  `operation_type`, `status`, `date`, `completed_at`, `notes`, `partner_id`
  (supplier or customer), `source_location_id`, `destination_location_id`,
  `company_id`.
- **Operation line:** `operation_id`, `product_id`, `quantity` (movements, must
  be greater than 0), `counted_quantity` (adjustments, must be 0 or more).

Location requirements for each operation type are in [workflow.md](workflow.md).

## Authentication

- **Password OTP:** `user_id`, `code_hash`, `expires_at`, `attempts`, `used`.
  Codes have no company. Only administrators can read them. Codes that expired more than a day ago are
  removed automatically.

## Migrations

- `18.0.2.1.0`: converts the old free-text `category` column into category
  records, then drops the column.
