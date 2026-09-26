from odoo import api, fields, models


class ProductCategory(models.Model):
    _name = "stocksense.product.category"
    _description = "StockSense Product Category"
    _order = "name, id"

    name = fields.Char(required=True, index=True)
    # Empty company makes a category available to every company.
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    product_ids = fields.One2many("stocksense.product", "category_id")
    product_count = fields.Integer(compute="_compute_product_count")
    _sql_constraints = [("name_company_unique", "unique(name, company_id)", "Category name must be unique within a company.")]

    @api.depends("product_ids")
    def _compute_product_count(self):
        for category in self:
            category.product_count = len(category.product_ids)
