from odoo import Command
from odoo.tests.common import TransactionCase, new_test_user


class StockSenseCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.user = new_test_user(cls.env, login="stocksense_test_user", groups="base.group_user", company_id=cls.company.id)
        cls.warehouse = cls.env["stocksense.warehouse"].create({"name": "Test Warehouse", "code": "TEST"})
        cls.source = cls.env["stocksense.location"].create({"name": "Rack A", "warehouse_id": cls.warehouse.id})
        cls.destination = cls.env["stocksense.location"].create({"name": "Rack B", "warehouse_id": cls.warehouse.id})
        cls.product = cls.env["stocksense.product"].create({"name": "Steel Rod", "sku": "TEST-ROD"})
        cls.other_product = cls.env["stocksense.product"].create({"name": "Bolt", "sku": "TEST-BOLT"})
        cls.partner = cls.env["res.partner"].create({"name": "Test Supplier"})

    def operation(self, kind="receipt", quantity=10, **values):
        defaults = {
            "operation_type": kind, "partner_id": self.partner.id,
            "source_location_id": self.source.id if kind in ("delivery", "transfer") else False,
            "destination_location_id": self.destination.id if kind == "transfer" else self.source.id if kind in ("receipt", "adjustment") else False,
            "line_ids": [Command.create({"product_id": self.product.id, "quantity": quantity, "counted_quantity": quantity})],
        }
        defaults.update(values)
        return self.env["stocksense.operation"].with_user(self.user).create(defaults)

    def stock(self, product=None, location=None):
        return self.env["stocksense.inventory.service"]._get_stock(product or self.product, location or self.source)

    def seed(self, quantity=10):
        operation = self.operation(quantity=quantity)
        operation.action_validate()
        return operation
