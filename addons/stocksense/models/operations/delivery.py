from odoo import models


class Delivery(models.Model):
    _inherit = "stocksense.operation"

    def _apply_delivery(self, service):
        for line in self.line_ids:
            service._decrease_stock(line, self.source_location_id)
