from odoo import models, _
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_round


class InventoryService(models.AbstractModel):
    _name = "stocksense.inventory.service"
    _description = "StockSense Inventory Service"

    # Private methods cannot be called through Odoo RPC. Public operation actions
    # validate access, company and quantities before reaching these methods.
    def _get_stock(self, product, location):
        stock = self.env["stocksense.stock"].search([
            ("product_id", "=", product.id), ("location_id", "=", location.id),
        ], limit=1)
        return stock.quantity if stock else 0.0

    def _lock_balances(self, operation):
        # A stable product/location lock also covers a balance that does not yet
        # exist. Ordered acquisition prevents opposite transfers deadlocking.
        if operation.operation_type == "transfer":
            locations = operation.source_location_id | operation.destination_location_id
        elif operation.operation_type == "delivery":
            locations = operation.source_location_id
        else:
            locations = operation.destination_location_id
        keys = sorted({(line.product_id.id, loc.id) for line in operation.line_ids for loc in locations})
        for product_id, location_id in keys:
            self.env.cr.execute("SELECT pg_advisory_xact_lock(%s, %s)", [product_id, location_id])
            # Under REPEATABLE READ, another transaction may have inserted the
            # first balance after our snapshot. UPSERT converts that race into
            # a serialization failure, which Odoo retries, rather than a unique
            # constraint error. It also locks existing rows without changing stock.
            self.env.cr.execute("""
                INSERT INTO stocksense_stock
                    (product_id, location_id, company_id, quantity, create_uid, write_uid, create_date, write_date)
                VALUES (%s, %s, %s, 0, %s, %s, NOW() AT TIME ZONE 'UTC', NOW() AT TIME ZONE 'UTC')
                ON CONFLICT (product_id, location_id)
                DO UPDATE SET quantity = stocksense_stock.quantity
            """, [product_id, location_id, operation.company_id.id, self.env.uid, self.env.uid])
        self.env["stocksense.stock"].invalidate_model()

    def _set_stock(self, line, location, quantity):
        operation = line.operation_id
        if line.product_id.company_id != operation.company_id or location.company_id != operation.company_id:
            raise ValidationError(_("Product, location and operation must belong to the same company."))
        quantity = float_round(quantity, precision_digits=3)
        if quantity < 0:
            raise ValidationError(_("Insufficient stock for %(product)s at %(location)s.", product=line.product_id.display_name, location=location.display_name))
        stock = self.env["stocksense.stock"].search([
            ("product_id", "=", line.product_id.id), ("location_id", "=", location.id),
        ], limit=1)
        before = stock.quantity if stock else 0.0
        if stock:
            stock.sudo().write({"quantity": quantity})
        else:
            self.env["stocksense.stock"].sudo().create({"product_id": line.product_id.id, "location_id": location.id, "quantity": quantity})
        self.env["stocksense.stock.ledger"].sudo().create({
            "product_id": line.product_id.id, "location_id": location.id,
            "operation_id": operation.id, "operation_line_id": line.id,
            "quantity_before": before, "quantity_change": quantity - before,
            "quantity_after": quantity, "user_id": self.env.uid,
        })

    def _increase_stock(self, line, location):
        self._set_stock(line, location, self._get_stock(line.product_id, location) + line.quantity)

    def _decrease_stock(self, line, location):
        self._set_stock(line, location, self._get_stock(line.product_id, location) - line.quantity)

    def _move_stock(self, line, source, destination):
        self._decrease_stock(line, source)
        self._increase_stock(line, destination)

    def _adjust_stock(self, line, location):
        self._set_stock(line, location, line.counted_quantity)
