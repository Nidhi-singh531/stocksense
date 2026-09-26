from odoo import models


class Adjustment(models.Model):
    _inherit = "stocksense.operation"

    def _apply_adjustment(self, service):
        for line in self.line_ids:
            service._adjust_stock(line, self.destination_location_id)
