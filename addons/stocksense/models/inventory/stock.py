from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class Stock(models.Model):
    _name = "stocksense.stock"
    _description = "StockSense Stock Balance"
    _rec_name = "product_id"
    _check_company_auto = True

    product_id = fields.Many2one("stocksense.product", required=True, ondelete="restrict", check_company=True, index=True)
    location_id = fields.Many2one("stocksense.location", required=True, ondelete="restrict", check_company=True, index=True)
    company_id = fields.Many2one(related="location_id.company_id", store=True, index=True)
    quantity = fields.Float(required=True, default=0, digits=(16, 3))
    _sql_constraints = [
        ("product_location_unique", "unique(product_id, location_id)", "Only one balance is allowed per product and location."),
        ("quantity_nonnegative", "CHECK(quantity >= 0)", "Stock cannot be negative."),
    ]

    def _require_service(self):
        if not self.env.su:
            raise AccessError(_("Stock balances can only be changed by validating an operation."))

    @api.model_create_multi
    def create(self, vals_list):
        self._require_service()
        return super().create(vals_list)

    def write(self, vals):
        self._require_service()
        return super().write(vals)

    def unlink(self):
        self._require_service()
        return super().unlink()
