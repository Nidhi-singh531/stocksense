from odoo import models


class Receipt(models.Model):
    _inherit = "stocksense.operation"

    def _apply_receipt(self, service):
        for line in self.line_ids:
            service._increase_stock(line, self.destination_location_id)
