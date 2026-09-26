# Team workflow

Use Odoo 18 and Python 3.11. All work lives in this one project. Each area has
an owner who reviews changes to it:

- Member 1 ([verifiedanu](https://github.com/verifiedanu)) owns `models/inventory/`, `services/` and `tests/test_inventory.py`.
- Member 2 ([Nidhi-singh531](https://github.com/Nidhi-singh531), repo owner) owns `models/operations/` and `tests/test_operations.py`.
- Member 3 ([Pri-max11](https://github.com/Pri-max11)) owns `views/`, `static/`,
  `controllers/`, `models/dashboard.py`, `models/password_otp.py`,
  `models/res_users.py`, `tests/test_dashboard.py` and `tests/test_auth.py`.
- Member 2, as repo owner, also owns `__manifest__.py`, the root `__init__.py` files,
  `security/` and `data/`.

Rules:

- After the submission, do not commit directly to `main`. Work on a branch and merge after the owner
  of each changed area has reviewed it.
- Stock changes only through the inventory service. Never write
  `stocksense.stock` or ledger rows from other code.
- Add access rights and company rules in the same change that adds a model.
- Run `.\scripts\start-odoo.ps1 -Database stocksense_test -Test` before
  merging. It must exit with code 0, and its summary line must read
  `0 failed, 0 error(s) of N tests`, where N is greater than 0.
- Bump the version in `__manifest__.py` and add a migration when a change
  alters existing data.
- Update the "Status by requirement", "What has been done" and "What remains"
  sections of README.md with every change.
- Never commit database credentials, `config/odoo.conf`, virtual environments,
  the `.local/` folder or the Odoo source.
