import math
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ReorderRule(models.Model):
    _name = "stocksense.reorder.rule"
    _description = "StockSense Reorder Rule"
    _rec_name = "product_id"
    _check_company_auto = True

    product_id = fields.Many2one("stocksense.product", required=True, ondelete="cascade", check_company=True)
    location_id = fields.Many2one("stocksense.location", required=True, ondelete="cascade", check_company=True)
    company_id = fields.Many2one(related="location_id.company_id", store=True)
    minimum_quantity = fields.Float(required=True, default=5, digits=(16, 3))
    target_quantity = fields.Float(required=True, default=10, digits=(16, 3))
    quantity_on_hand = fields.Float(compute="_compute_stock", digits=(16, 3))
    suggested_quantity = fields.Float(compute="_compute_stock", digits=(16, 3))
    below_minimum = fields.Boolean(compute="_compute_stock", search="_search_below_minimum")
    _sql_constraints = [("product_location_unique", "unique(product_id, location_id)", "A reorder rule already exists for this product and location.")]

    @api.constrains("minimum_quantity", "target_quantity")
    def _check_quantities(self):
        for rule in self:
            if not all(math.isfinite(q) for q in (rule.minimum_quantity, rule.target_quantity)) or not 0 <= rule.minimum_quantity <= rule.target_quantity:
                raise ValidationError(_("Target quantity must be at least the minimum, and both must be nonnegative."))

    def _compute_stock(self):
        for rule in self:
            rule.quantity_on_hand = self.env["stocksense.inventory.service"]._get_stock(rule.product_id, rule.location_id)
            rule.below_minimum = rule.quantity_on_hand < rule.minimum_quantity
            rule.suggested_quantity = max(0, rule.target_quantity - rule.quantity_on_hand) if rule.below_minimum else 0

    def _search_below_minimum(self, operator, value):
        if operator not in ("=", "!=") or not isinstance(value, bool):
            raise NotImplementedError(_("Unsupported search on below minimum."))
        below = self.search([]).filtered("below_minimum").ids
        return [("id", "in" if (operator == "=") == value else "not in", below)]
