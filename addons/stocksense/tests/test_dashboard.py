from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import new_test_user
from .common import StockSenseCase


@tagged("post_install", "-at_install")
class TestDashboard(StockSenseCase):
    def test_counts_follow_operations(self):
        dashboard = self.env["stocksense.dashboard"].with_user(self.user)
        before = dashboard.get_summary()
        receipt = self.operation()
        after = dashboard.get_summary()
        self.assertEqual(after["receipts"], before["receipts"] + 1)
        receipt.action_validate()
        after = dashboard.get_summary()
        self.assertEqual(after["receipts"], before["receipts"])
        self.assertNotIn(self.product.id, after["empty_product_ids"])

    def test_low_stock_alert(self):
        self.seed(2)
        rule = self.env["stocksense.reorder.rule"].create({"product_id": self.product.id, "location_id": self.source.id, "minimum_quantity": 5, "target_quantity": 10})
        summary = self.env["stocksense.dashboard"].with_user(self.user).get_summary()
        item = next(item for item in summary["low_items"] if item["id"] == rule.id)
        self.assertEqual(item["suggested"], 8)

    def test_filters_scope_kpis_and_operations(self):
        category = self.env["stocksense.product.category"].create({"name": "Metals"})
        self.product.category_id = category
        other_warehouse = self.env["stocksense.warehouse"].create({"name": "Second", "code": "SEC"})
        other_location = self.env["stocksense.location"].create({"name": "Bay 1", "warehouse_id": other_warehouse.id})
        self.seed(5)
        self.operation(destination_location_id=other_location.id)
        dashboard = self.env["stocksense.dashboard"].with_user(self.user)

        in_first = dashboard.get_summary({"warehouse_id": self.warehouse.id})
        in_second = dashboard.get_summary({"warehouse_id": other_warehouse.id})
        self.assertNotIn(self.product.id, in_first["empty_product_ids"])
        self.assertIn(self.product.id, in_second["empty_product_ids"])
        self.assertEqual(in_second["receipts"], 1)
        self.assertEqual(in_first["receipts"], 0)

        done = dashboard.get_summary({"status": "done", "operation_type": "receipt", "location_id": self.source.id})
        self.assertEqual({op["status"] for op in done["recent"]}, {"done"})
        self.assertEqual(done["operations_count"], 1)

        metals = dashboard.get_summary({"category_id": category.id})
        self.assertEqual(metals["products"], 1)
        self.assertEqual(metals["operations_count"], 2)

    def test_invalid_filters_are_ignored(self):
        summary = self.env["stocksense.dashboard"].with_user(self.user).get_summary({"status": "bogus", "warehouse_id": "x; drop", "category_id": -3})
        self.assertEqual(summary["filters"], {})

    def test_portal_user_cannot_read_dashboard(self):
        portal = new_test_user(self.env, login="stocksense_portal", groups="base.group_portal")
        with self.assertRaises(AccessError):
            self.env["stocksense.dashboard"].with_user(portal).get_summary()
