from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class Ledger(models.Model):
    _name = "stocksense.stock.ledger"
    _description = "StockSense Stock Ledger"
    _order = "date desc, id desc"
    _check_company_auto = True

    date = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    product_id = fields.Many2one("stocksense.product", required=True, ondelete="restrict", check_company=True, index=True)
    location_id = fields.Many2one("stocksense.location", required=True, ondelete="restrict", check_company=True)
    company_id = fields.Many2one(related="location_id.company_id", store=True, index=True)
    operation_id = fields.Many2one("stocksense.operation", required=True, ondelete="restrict", check_company=True, index=True)
    operation_type = fields.Selection(related="operation_id.operation_type", store=True, index=True)
    operation_line_id = fields.Many2one("stocksense.operation.line", required=True, ondelete="restrict")
    quantity_before = fields.Float(digits=(16, 3), required=True)
    quantity_change = fields.Float(digits=(16, 3), required=True)
    quantity_after = fields.Float(digits=(16, 3), required=True)
    user_id = fields.Many2one("res.users", required=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            raise AccessError(_("Ledger entries are created by the inventory service."))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_("Posted ledger entries cannot be edited. Use an adjustment."))

    @api.ondelete(at_uninstall=False)
    def _prevent_deletion(self):
        raise AccessError(_("Posted ledger entries cannot be deleted."))
