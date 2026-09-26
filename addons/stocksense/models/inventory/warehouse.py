from odoo import fields, models, _
from odoo.exceptions import UserError


class Warehouse(models.Model):
    _name = "stocksense.warehouse"
    _description = "StockSense Warehouse"
    _check_company_auto = True

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    location_ids = fields.One2many("stocksense.location", "warehouse_id")
    _sql_constraints = [("code_company_unique", "unique(code, company_id)", "Warehouse code must be unique within a company.")]

    def write(self, vals):
        if "company_id" in vals and any(warehouse.location_ids and warehouse.company_id.id != vals["company_id"] for warehouse in self):
            raise UserError(_("A warehouse with locations cannot change company."))
        return super().write(vals)
