# StockSense

StockSense is an inventory management app built as an Odoo 18 Community addon.
It replaces paper registers and spreadsheets with one place to track products,
stock at each location, and every stock movement. It is built for inventory
managers and warehouse staff.

> **Status (26 Sep 2026, submission):** every functional requirement in the
> problem statement is built and tested (43 automated tests pass, and a browser
> check of every screen passes). Four items work with a limitation (🟡), and
> the screens have not yet been compared with the Excalidraw mockup (⬜). See
> [What remains](#what-remains).

## Contents

- [Status by requirement](#status-by-requirement)
- [The plan](#the-plan)
- [What has been done](#what-has-been-done)
- [What remains](#what-remains)
- [How it works](#how-it-works)
- [Setup on Windows](#setup-on-windows)
- [Running the tests](#running-the-tests)
- [Using the app](#using-the-app)
- [Project layout](#project-layout)

## Status by requirement

Legend: ✅ done and tested · 🟡 done with a limitation · ⬜ not started

| Requirement from the problem statement | Status | Notes |
| --- | --- | --- |
| Sign up and log in | ✅ | New sign-ups become internal users with full StockSense access. There is no separate manager or staff role yet. |
| OTP-based password reset | 🟡 | Works end to end. Real emails need an outgoing mail server. |
| Redirect to the dashboard after login | ✅ | Also applies after sign-up and after a password reset. |
| KPI: total products in stock | 🟡 | The card counts all active products, including those with zero stock (also shown under Out of stock). It follows the category filter, not the warehouse or location filter. |
| KPI: low stock and out of stock | ✅ | Low stock is based on reordering rules. |
| KPI: pending receipts, pending deliveries, transfers scheduled | ✅ | Pending means Draft, Waiting or Ready. |
| Filters: document type, status, warehouse or location, product category | ✅ | On the dashboard, plus search filters on every list. |
| Products: create and update, stock per location, categories, reordering rules | ✅ | |
| Product fields: name, SKU, category, unit of measure, optional initial stock | ✅ | Initial stock is posted as a logged adjustment. |
| Receipts: supplier, products, quantities, validate increases stock | ✅ | |
| Delivery orders: pick, pack, validate decreases stock | ✅ | Confirm, then "Picked & Packed", then Validate. Insufficient stock is blocked. |
| Internal transfers, logged in the ledger | ✅ | Total stock is unchanged; only the location changes. |
| Stock adjustments: enter counted quantity, auto-update and log | ✅ | |
| Move history (stock ledger) | ✅ | Read-only. Entries cannot be edited or deleted. |
| Settings: warehouses | ✅ | Warehouses and their locations. |
| Profile menu: My Profile, Logout | 🟡 | Uses Odoo's user menu (top right), not a left sidebar. |
| Alerts for low stock | 🟡 | Shown on the dashboard and in a "Below Minimum" filter. No email or push alerts. |
| Multi-warehouse support | ✅ | Multi-company data separation too. |
| SKU search and smart filters | ✅ | Products, operations, stock and move history search by SKU. |
| Matches the Excalidraw mockup | ⬜ | Not reviewed against the mockup yet. |

## The plan

The team plan splits the work into three areas in one shared addon. We
originally planned one Git branch per member. **All three areas now live in
this one project**, so the split is about who owns and reviews each folder,
not about branches.

| Area | Owner | Files | Question it answers |
| --- | --- | --- | --- |
| Inventory core | Member 1 ([verifiedanu](https://github.com/verifiedanu)) | `models/inventory/`, `services/`, `tests/test_inventory.py` | What products exist, where are they, and how much is there? |
| Operations | Member 2 ([Nidhi-singh531](https://github.com/Nidhi-singh531)) | `models/operations/`, `tests/test_operations.py` | What happens when someone receives, delivers, moves or counts stock? |
| UI, dashboard and auth | Member 3 ([Pri-max11](https://github.com/Pri-max11)) | `views/`, `static/`, `controllers/`, `models/dashboard.py`, `models/password_otp.py`, `models/res_users.py`, `tests/test_dashboard.py`, `tests/test_auth.py` | How do users see and use all of it? |
| Shared files | Member 2 (repo owner) | `__manifest__.py`, root `__init__.py` files, `security/`, `data/` | |

Phases:

1. **Phase 0, environment.** PostgreSQL, Python 3.11, Odoo 18 source next to
   this repository, no Docker. ✅
2. **Phases 1–2, skeleton.** An empty addon that installs. ✅
3. **Phase 3, shared contract.** Agree on model names and the inventory service
   (see [docs/architecture.md](docs/architecture.md)). ✅
4. **Inventory core.** Products, warehouses, locations, stock balances, ledger,
   reordering rules and the inventory service. ✅
5. **Operations.** Receipt first, then delivery, transfer and adjustment. ✅
6. **UI.** Menus, list and form views, the dashboard and its filters. ✅
7. **Authentication.** Sign-up, OTP reset and dashboard redirect. ✅
8. **Integration and verification.** Automated tests, a concurrency check and
   a browser check of every screen. ✅
9. **Submission.** Each member pushed their own area to `main` from their own
   GitHub account on 26 Sep 2026. ✅ Mockup review, team review and a demo
   dataset follow. See [What remains](#what-remains).

## What has been done

**Inventory core** (`models/inventory/`, `services/inventory_service.py`)

- Products with a unique SKU per company, a category, a unit of measure and
  optional initial stock. Products display and search as `[SKU] Name`.
- Product categories as a managed list, with a product count for each.
- Warehouses with codes, and locations inside them, shown as `WH/Rack A`.
- One stock balance per product and location, which can never go negative.
- A stock ledger that records the quantity before, the change and the quantity
  after, with the user and the originating operation. It cannot be edited or
  deleted.
- Reordering rules with a minimum and target. Each rule computes the suggested
  reorder quantity and can be filtered by "Below Minimum".
- The inventory service is the only code that changes stock. It locks the
  affected balances, rejects insufficient stock, and writes the ledger.

**Operations** (`models/operations/`)

- A single operation model for receipts, deliveries, internal transfers and
  adjustments, with references like `SS/2026/00001`.
- Workflow: Draft, Waiting, Ready, Done and Canceled. Validation is available
  from any open status.
- Validation is all-or-nothing. If any line fails, nothing is posted.
- Protections: an operation cannot be validated twice. Done operations cannot
  be edited. Nobody can set a status by hand. Quantities must be positive, with
  at most three decimals. Transfers need different source and destination
  locations. Each product can be counted only once per adjustment.
- Simultaneous validations are safe. This was checked with a separate
  concurrency script in addition to the tests.

**Dashboard and UI** (`views/`, `static/src/`, `models/dashboard.py`)

- Menus that follow the problem statement: Dashboard; Products (Products,
  Stock by Location, Categories, Reordering Rules); Operations (Receipts,
  Delivery Orders, Internal Transfers, Inventory Adjustments, All Operations);
  Move History; Settings (Warehouses, Locations).
- The dashboard has six KPI cards, and each opens the matching records. It also
  has quick actions, a recent operations list, a "Needs replenishment" list,
  and filters for document type, status, warehouse, location and category. It
  works on phone screens.
- Search filters on products, operations, stock and move history by SKU,
  warehouse, location, category, operation type and status.
- An app icon.

**Authentication** (`controllers/auth.py`, `models/password_otp.py`, `models/res_users.py`)

- Sign-up from the login page ("Don't have an account?") creates an internal
  user who lands on the dashboard.
- "Forgot password?" emails a 6-digit code. The code expires after 10 minutes
  and works once. It locks after 5 wrong attempts, and a new code can be sent
  once a minute. Codes are stored hashed. The page never reveals whether an
  account exists.
- After login, users go to the dashboard unless they were heading to a
  specific page.

**Quality**

- 43 automated tests: 9 inventory, 20 operations, 5 dashboard and 9
  authentication. They pass both on a fresh database and on an upgraded one.
- A migration turns the old free-text product category into category records
  when an existing database is upgraded.
- Access rules keep each company's data separate. Portal users cannot see
  inventory data.

## What remains

After submission, in priority order:

1. **Team review.** Each owner reviews their area (see [The plan](#the-plan)).
2. **Compare with the mockup.** Review the screens against the
   [Excalidraw mockup](https://link.excalidraw.com/l/65VNwvy7c4X/3ENvQFu9o8R)
   and adjust the layout and labels.
3. **Set up outgoing email.** Required for OTP codes to reach users. See
   [Password reset emails](#password-reset-emails).
4. **Decide the sign-up policy.** Right now anyone who can open the login page
   can create an internal account with full StockSense access: create, edit and
   delete products, warehouses and operations, and validate stock. That is fine
   for a demo. For real use,
   turn off sign-up (Settings → General Settings → Permissions → Customer
   Account: On invitation) or add an approval step.
5. **Profile menu placement.** If the mockup needs My Profile and Logout in a
   left sidebar, build it. Today they are in Odoo's top-right user menu.
6. **Demo data.** A script or data file with sample warehouses, products and
   operations for presentations.
7. **Separate manager and staff roles.** Today every internal user has the same
   StockSense rights.
8. **Share the extra checks.** The concurrency and browser checks live in the
   Git-ignored `.local/` folder. Move them into `scripts/` so the whole team
   can run them.

Possible later improvements, not required by the problem statement: reserving
stock when an operation is marked Ready, email or activity alerts for low
stock, unit-of-measure conversion, barcode scanning, and exporting move history.

## How it works

```text
            Views, dashboard, login pages          (Member 3)
                          │  buttons, forms
                          ▼
     Operations: receipt · delivery · transfer · adjustment   (Member 2)
                          │  action_validate()
                          ▼
                 stocksense.inventory.service       (Member 1)
                   locks · checks · updates
                  ┌───────┴────────┐
                  ▼                ▼
          stocksense.stock   stocksense.stock.ledger
         (balance per         (one row per change,
         product+location)     never edited)
```

Rules that hold everywhere:

- Stock changes only when an operation is validated, through the inventory
  service. Nothing else writes stock quantities.
- Every change creates a ledger row that links to its operation.
- Initial stock on a new product is posted as an adjustment, so it appears in
  the ledger too.

Models: `stocksense.product`, `stocksense.product.category`,
`stocksense.warehouse`, `stocksense.location`, `stocksense.stock`,
`stocksense.stock.ledger`, `stocksense.reorder.rule`, `stocksense.operation`,
`stocksense.operation.line`, `stocksense.password.otp`. Details are in
[docs/architecture.md](docs/architecture.md) and
[docs/database-design.md](docs/database-design.md). Operation behaviour is in
[docs/workflow.md](docs/workflow.md).

## Setup on Windows

Expected paths. The Odoo source lives next to this repository, never inside it:

```text
C:\Projects\odoo
C:\Projects\.venv-odoo18
C:\Projects\stocksense
```

Install Python 3.11 and PostgreSQL, then from PowerShell:

```powershell
git clone --depth 1 --branch 18.0 https://github.com/odoo/odoo.git C:\Projects\odoo
py -3.11 -m venv C:\Projects\.venv-odoo18
C:\Projects\.venv-odoo18\Scripts\python.exe -m pip install -r C:\Projects\odoo\requirements.txt
```

In pgAdmin, create a PostgreSQL LOGIN role named `odoo` with "Create
databases" enabled and without superuser. Odoo must not connect as `postgres`.

Copy the example configuration and set both passwords. `db_password` is the
PostgreSQL role password. `admin_passwd` is the Odoo database-manager master
password. `config/odoo.conf` is ignored by Git and must never be committed.

```powershell
cd C:\Projects\stocksense
Copy-Item config\odoo.conf.example config\odoo.conf
# Edit config/odoo.conf, then install and start:
.\scripts\start-odoo.ps1 -Database stocksense_dev -Install
.\scripts\start-odoo.ps1 -Database stocksense_dev
```

Open http://localhost:8069. A database created by `-Install` has the login
`admin` with password `admin`. Change it straight away.

After pulling new changes, upgrade the module:

```powershell
.\scripts\start-odoo.ps1 -Database stocksense_dev -Upgrade
```

### Password reset emails

OTP codes are sent by email. In developer mode, add an outgoing mail server
under Settings → Technical → Outgoing Mail Servers. For local work without a
mail server, run Odoo directly in developer mode (the start script cannot pass
extra options):

```powershell
C:\Projects\.venv-odoo18\Scripts\python.exe C:\Projects\odoo\odoo-bin -c config\odoo.conf -d stocksense_dev --dev all
```

When sending fails, the code is written to the server log. The user must have an
email address set, or no code is issued.

## Running the tests

Always test on a separate, disposable database, never on your working one:

```powershell
.\scripts\start-odoo.ps1 -Database stocksense_test -Test
```

This installs or updates the module and runs all StockSense tests. HTTP tests
use port 8079, so they can run while your development server is on 8069. The
last line should read `0 failed, 0 error(s)`.

## Using the app

1. **Settings → Warehouses:** create a warehouse and add its locations.
2. **Products → Categories:** add categories, or create them from the product
   form.
3. **Products → Products:** add products. You can enter initial stock and its
   location.
4. **Products → Reordering Rules:** set minimum and target quantities to get
   low-stock alerts.
5. **Operations:** create receipts, deliveries, transfers or counts, then
   **Validate** to post them.
6. **Move History:** every change, who made it and why.
7. **Dashboard:** what needs attention, filtered however you need.

## Project layout

```text
stocksense/
├── README.md                  This file: plan, status and setup
├── CONTRIBUTING.md            Team rules
├── config/odoo.conf.example   Copy to odoo.conf (ignored by Git)
├── docs/                      Architecture, database design, workflow
├── scripts/start-odoo.ps1     Install, upgrade, run and test
└── addons/stocksense/
    ├── __manifest__.py        Depends on base, web, mail, auth_signup
    ├── models/
    │   ├── inventory/         category, product, warehouse, location, stock, ledger, reorder_rule
    │   ├── operations/        operation, receipt, delivery, transfer, adjustment
    │   ├── dashboard.py       KPI and filter queries
    │   ├── password_otp.py    OTP codes
    │   └── res_users.py       Sign-up creates internal users
    ├── services/inventory_service.py
    ├── controllers/           dashboard.py, auth.py (login redirect, OTP pages)
    ├── views/                 inventory, operation, menu and auth views
    ├── static/                Dashboard JS, template and CSS; app icon
    ├── security/              Access rights and company rules
    ├── data/                  Operation sequence, sign-up settings
    ├── migrations/            Upgrade scripts
    └── tests/                 test_inventory, test_operations, test_dashboard, test_auth
```
