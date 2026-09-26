from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Location(models.Model):
    _name = "stocksense.location"
    _description = "StockSense Location"
    _check_company_auto = True

    name = fields.Char(required=True)
    warehouse_id = fields.Many2one("stocksense.warehouse", required=True, ondelete="restrict", check_company=True)
    company_id = fields.Many2one(related="warehouse_id.company_id", store=True)
    _sql_constraints = [("name_warehouse_unique", "unique(name, warehouse_id)", "Location name must be unique within its warehouse.")]

    @api.depends("name", "warehouse_id.code")
    def _compute_display_name(self):
        for location in self:
            location.display_name = f"{location.warehouse_id.code}/{location.name}" if location.warehouse_id else location.name

    def write(self, vals):
        if "warehouse_id" in vals and any(loc.warehouse_id.id != vals["warehouse_id"] for loc in self):
            if self.env["stocksense.operation"].sudo().search_count(["|", ("source_location_id", "in", self.ids), ("destination_location_id", "in", self.ids)], limit=1):
                raise UserError(_("A location used in operations cannot change warehouse. Use an internal transfer."))
        return super().write(vals)
