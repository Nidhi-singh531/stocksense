from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class Product(models.Model):
    _name = "stocksense.product"
    _description = "StockSense Product"
    _order = "name, id"
    _check_company_auto = True
    _rec_names_search = ["name", "sku"]

    name = fields.Char(required=True, index=True)
    sku = fields.Char(string="SKU", required=True, index=True)
    category_id = fields.Many2one("stocksense.product.category", string="Category", index=True, ondelete="restrict", check_company=True)
    unit_of_measure = fields.Selection([
        ("units", "Units"), ("kg", "Kilograms"), ("liters", "Liters"),
        ("meters", "Meters"), ("boxes", "Boxes"),
    ], required=True, default="units")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    stock_ids = fields.One2many("stocksense.stock", "product_id")
    quantity_on_hand = fields.Float(compute="_compute_quantity", digits=(16, 3))
    # Creation-only inputs. create() turns them into an opening adjustment so
    # the initial quantity is posted and logged like any other stock change.
    initial_quantity = fields.Float(string="Initial Stock", compute="_compute_initial_stock", readonly=False, digits=(16, 3))
    initial_location_id = fields.Many2one("stocksense.location", string="Initial Location", compute="_compute_initial_stock", readonly=False, check_company=True)

    _sql_constraints = [("sku_company_unique", "unique(sku, company_id)", "SKU must be unique within a company.")]

    @api.depends("stock_ids.quantity")
    def _compute_quantity(self):
        for product in self:
            product.quantity_on_hand = sum(product.stock_ids.mapped("quantity"))

    def _compute_initial_stock(self):
        for product in self:
            product.initial_quantity = 0
            product.initial_location_id = False

    @api.depends("name", "sku")
    def _compute_display_name(self):
        for product in self:
            product.display_name = f"[{product.sku}] {product.name}" if product.sku else product.name

    @api.model_create_multi
    def create(self, vals_list):
        openings = []
        for vals in vals_list:
            quantity = vals.pop("initial_quantity", 0) or 0
            location_id = vals.pop("initial_location_id", False)
            if quantity and not location_id:
                raise ValidationError(_("Choose a location for the initial stock."))
            openings.append((quantity, location_id))
        products = super().create(vals_list)
        for product, (quantity, location_id) in zip(products, openings):
            if quantity:
                adjustment = self.env["stocksense.operation"].create({
                    "operation_type": "adjustment", "company_id": product.company_id.id,
                    "destination_location_id": location_id, "notes": _("Initial stock"),
                    "line_ids": [Command.create({"product_id": product.id, "counted_quantity": quantity})],
                })
                adjustment.action_validate()
        return products

    def write(self, vals):
        vals.pop("initial_quantity", None)
        vals.pop("initial_location_id", None)
        if {"company_id", "unit_of_measure"} & vals.keys():
            for product in self:
                changed = ("company_id" in vals and vals["company_id"] != product.company_id.id) or ("unit_of_measure" in vals and vals["unit_of_measure"] != product.unit_of_measure)
                if changed and self.env["stocksense.operation.line"].sudo().search_count([("product_id", "=", product.id)], limit=1):
                    raise UserError(_("A product used in operations cannot change company or unit of measure. Create a new product instead."))
        return super().write(vals)
