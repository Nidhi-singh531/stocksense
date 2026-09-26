from odoo import Command
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from .common import StockSenseCase


@tagged("post_install", "-at_install")
class TestOperations(StockSenseCase):
    def test_receipt_posts_stock_and_audit(self):
        receipt = self.seed(50)
        self.assertEqual(self.stock(), 50)
        self.assertEqual(receipt.status, "done")
        self.assertTrue(receipt.completed_at)
        self.assertEqual(len(receipt.ledger_ids), 1)
        self.assertEqual(receipt.ledger_ids.quantity_change, 50)
        self.assertEqual(receipt.ledger_ids.user_id, self.user)

    def test_delivery_decreases_stock(self):
        self.seed(50)
        delivery = self.operation("delivery", 12)
        delivery.action_validate()
        self.assertEqual(self.stock(), 38)
        self.assertEqual(delivery.ledger_ids.quantity_change, -12)

    def test_transfer_preserves_total(self):
        self.seed(50)
        transfer = self.operation("transfer", 20)
        transfer.action_validate()
        self.assertEqual(self.stock(), 30)
        self.assertEqual(self.stock(location=self.destination), 20)
        self.assertEqual(sum(transfer.ledger_ids.mapped("quantity_change")), 0)
        self.assertEqual(len(transfer.ledger_ids), 2)

    def test_adjustment_sets_absolute_count(self):
        self.seed(50)
        adjustment = self.operation("adjustment", 47)
        adjustment.action_validate()
        self.assertEqual(self.stock(), 47)
        self.assertEqual(adjustment.ledger_ids.quantity_change, -3)

    def test_zero_count_clears_stock(self):
        self.seed(3)
        self.operation("adjustment", 0).action_validate()
        self.assertEqual(self.stock(), 0)

    def test_insufficient_stock_rolls_back(self):
        self.seed(2)
        delivery = self.operation("delivery", 3)
        with self.assertRaises(ValidationError):
            delivery.action_validate()
        self.assertEqual(self.stock(), 2)
        self.assertEqual(delivery.status, "draft")
        self.assertFalse(delivery.ledger_ids)

    def test_multiline_failure_rolls_back_first_line(self):
        self.seed(10)
        delivery = self.operation("delivery", 4)
        delivery.write({"line_ids": [Command.create({"product_id": self.other_product.id, "quantity": 1})]})
        with self.assertRaises(ValidationError):
            delivery.action_validate()
        self.assertEqual(self.stock(), 10)
        self.assertFalse(delivery.ledger_ids)
        self.assertEqual(delivery.status, "draft")

    def test_duplicate_product_lines_check_combined_quantity(self):
        self.seed(10)
        delivery = self.operation("delivery", 6)
        delivery.write({"line_ids": [Command.create({"product_id": self.product.id, "quantity": 6})]})
        with self.assertRaises(ValidationError):
            delivery.action_validate()
        self.assertEqual(self.stock(), 10)

    def test_validate_twice_does_not_post_twice(self):
        receipt = self.seed(5)
        with self.assertRaises(UserError):
            receipt.action_validate()
        self.assertEqual(self.stock(), 5)
        self.assertEqual(len(receipt.ledger_ids), 1)

    def test_done_header_and_lines_are_immutable(self):
        receipt = self.seed()
        for action in [lambda: receipt.write({"notes": "Changed"}),
                       lambda: receipt.line_ids.write({"quantity": 99}),
                       lambda: receipt.line_ids.unlink(), lambda: receipt.unlink(),
                       lambda: receipt.action_cancel(), lambda: receipt.action_reset_draft(),
                       lambda: receipt.write({"line_ids": [Command.create({"product_id": self.product.id, "quantity": 1})]})]:
            with self.assertRaises(UserError):
                action()

    def test_canceled_operation_cannot_post(self):
        receipt = self.operation()
        receipt.action_cancel()
        with self.assertRaises(UserError):
            receipt.action_validate()
        self.assertEqual(self.stock(), 0)

    def test_workflow_does_not_reserve_or_move_stock(self):
        receipt = self.operation()
        receipt.action_confirm()
        self.assertEqual(receipt.status, "waiting")
        receipt.action_ready()
        self.assertEqual(receipt.status, "ready")
        self.assertEqual(self.stock(), 0)
        receipt.action_reset_draft()
        receipt.write({"notes": "Updated"})
        receipt.action_validate()
        self.assertEqual(self.stock(), 10)

    def test_cannot_forge_done_status(self):
        with self.assertRaises(UserError):
            self.operation(status="done")
        receipt = self.operation()
        with self.assertRaises(UserError):
            receipt.write({"status": "done"})

    def test_context_defaults_cannot_bypass_workflow(self):
        forged = self.env["stocksense.operation"].with_user(self.user).with_context(default_status="done").create({})
        self.assertEqual(forged.status, "draft")
        receipt = self.seed()
        with self.assertRaises(UserError):
            self.env["stocksense.operation.line"].with_user(self.user).with_context(default_operation_id=receipt.id).create({"product_id": self.product.id, "quantity": 3})

    def test_invalid_quantities(self):
        for quantity in (-1, 0, 0.0001, float("inf"), float("nan")):
            with self.assertRaises(ValidationError), self.env.cr.savepoint():
                self.operation(quantity=quantity)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.operation("adjustment", -1)

    def test_fractional_quantities(self):
        self.seed(1.125)
        self.operation("delivery", 0.125).action_validate()
        self.assertEqual(self.stock(), 1)

    def test_required_inputs(self):
        for values in [{"line_ids": []}, {"partner_id": False}, {"destination_location_id": False}]:
            receipt = self.operation(**values)
            with self.assertRaises(ValidationError):
                receipt.action_validate()

    def test_same_location_transfer_rejected(self):
        transfer = self.operation("transfer", destination_location_id=self.source.id)
        with self.assertRaises(ValidationError):
            transfer.action_validate()

    def test_duplicate_adjustment_count_rejected(self):
        adjustment = self.operation("adjustment", 5)
        adjustment.write({"line_ids": [Command.create({"product_id": self.product.id, "counted_quantity": 8})]})
        with self.assertRaises(ValidationError):
            adjustment.action_validate()

    def test_copy_starts_new_draft(self):
        receipt = self.seed()
        duplicate = receipt.copy()
        self.assertEqual(duplicate.status, "draft")
        self.assertNotEqual(duplicate.reference, receipt.reference)
        self.assertFalse(duplicate.completed_at)
        self.assertFalse(duplicate.ledger_ids)
