from odoo import models


class Transfer(models.Model):
    _inherit = "stocksense.operation"

    def _apply_transfer(self, service):
        for line in self.line_ids:
            service._move_stock(line, self.source_location_id, self.destination_location_id)
