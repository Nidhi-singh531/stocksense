from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from .common import StockSenseCase


@tagged("post_install", "-at_install")
class TestInventory(StockSenseCase):
    def test_stock_and_ledger_cannot_be_manually_edited(self):
        receipt = self.seed()
        stock = self.env["stocksense.stock"].with_user(self.user).search([("product_id", "=", self.product.id)])
        with self.assertRaises(AccessError):
            stock.write({"quantity": 100})
        with self.assertRaises(AccessError):
            stock.unlink()
        with self.assertRaises(AccessError):
            receipt.ledger_ids.write({"quantity_change": 100})
        with self.assertRaises(AccessError):
            receipt.ledger_ids.unlink()

    def test_product_total_and_reorder_rule(self):
        self.seed(4)
        rule = self.env["stocksense.reorder.rule"].create({"product_id": self.product.id, "location_id": self.source.id, "minimum_quantity": 5, "target_quantity": 10})
        self.assertEqual(self.product.quantity_on_hand, 4)
        self.assertEqual(rule.quantity_on_hand, 4)
        self.assertEqual(rule.suggested_quantity, 6)

    def test_initial_stock_posts_logged_adjustment(self):
        category = self.env["stocksense.product.category"].create({"name": "Furniture"})
        product = self.env["stocksense.product"].with_user(self.user).create({
            "name": "Chair", "sku": "CHAIR-1", "category_id": category.id,
            "initial_quantity": 25, "initial_location_id": self.source.id})
        self.assertEqual(self.stock(product), 25)
        ledger = self.env["stocksense.stock.ledger"].search([("product_id", "=", product.id)])
        self.assertEqual(ledger.quantity_change, 25)
        self.assertEqual(ledger.operation_type, "adjustment")
        self.assertEqual(category.product_count, 1)

    def test_initial_stock_requires_location(self):
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env["stocksense.product"].create({"name": "Desk", "sku": "DESK-1", "initial_quantity": 5})
        product = self.env["stocksense.product"].create({"name": "Desk", "sku": "DESK-2"})
        self.assertFalse(product.stock_ids)

    def test_sku_search_and_display(self):
        self.assertEqual(self.product.display_name, "[TEST-ROD] Steel Rod")
        self.assertEqual(self.source.display_name, "TEST/Rack A")
        found = self.env["stocksense.product"].name_search("TEST-ROD")
        self.assertEqual([row[0] for row in found], [self.product.id])

    def test_below_minimum_filter(self):
        self.seed(2)
        low = self.env["stocksense.reorder.rule"].create({"product_id": self.product.id, "location_id": self.source.id, "minimum_quantity": 5, "target_quantity": 10})
        fine = self.env["stocksense.reorder.rule"].create({"product_id": self.other_product.id, "location_id": self.source.id, "minimum_quantity": 0, "target_quantity": 0})
        rules = self.env["stocksense.reorder.rule"].search([("below_minimum", "=", True)])
        self.assertIn(low, rules)
        self.assertNotIn(fine, rules)

    def test_invalid_reorder_threshold(self):
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env["stocksense.reorder.rule"].create({"product_id": self.product.id, "location_id": self.source.id, "minimum_quantity": 10, "target_quantity": 5})

    def test_other_company_is_hidden_and_cannot_be_used(self):
        company = self.env["res.company"].create({"name": "Other StockSense Company"})
        product = self.env["stocksense.product"].create({"name": "Private Product", "sku": "PRIVATE", "company_id": company.id})
        self.assertFalse(self.env["stocksense.product"].with_user(self.user).search([("id", "=", product.id)]))
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self.operation(line_ids=[(0, 0, {"product_id": product.id, "quantity": 1})])

    def test_cross_company_location_rejected_even_for_admin(self):
        company = self.env["res.company"].create({"name": "Another Company"})
        warehouse = self.env["stocksense.warehouse"].create({"name": "Other", "code": "OTHER", "company_id": company.id})
        location = self.env["stocksense.location"].create({"name": "Other Rack", "warehouse_id": warehouse.id})
        with self.assertRaises(UserError), self.env.cr.savepoint():
            self.env["stocksense.operation"].create({"operation_type": "receipt", "destination_location_id": location.id})
