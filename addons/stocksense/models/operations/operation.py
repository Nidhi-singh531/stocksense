import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round


class Operation(models.Model):
    _name = "stocksense.operation"
    _description = "StockSense Operation"
    _rec_name = "reference"
    _order = "date desc, id desc"
    _check_company_auto = True

    reference = fields.Char(required=True, readonly=True, copy=False, default="New", index=True)
    operation_type = fields.Selection([
        ("receipt", "Receipt"), ("delivery", "Delivery"),
        ("transfer", "Internal Transfer"), ("adjustment", "Adjustment"),
    ], required=True, default="receipt", index=True)
    status = fields.Selection([
        ("draft", "Draft"), ("waiting", "Waiting"), ("ready", "Ready"),
        ("done", "Done"), ("canceled", "Canceled"),
    ], required=True, default="draft", readonly=True, copy=False, index=True)
    date = fields.Datetime(required=True, default=fields.Datetime.now)
    completed_at = fields.Datetime(readonly=True, copy=False)
    notes = fields.Text()
    partner_id = fields.Many2one("res.partner", string="Supplier / Customer", check_company=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    source_location_id = fields.Many2one("stocksense.location", ondelete="restrict", check_company=True)
    destination_location_id = fields.Many2one("stocksense.location", ondelete="restrict", check_company=True)
    line_ids = fields.One2many("stocksense.operation.line", "operation_id", copy=True)
    ledger_ids = fields.One2many("stocksense.stock.ledger", "operation_id", readonly=True)
    _sql_constraints = [("reference_unique", "unique(reference)", "Operation reference must be unique.")]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("status", "draft") != "draft" or vals.get("completed_at"):
                raise UserError(_("New operations must start in Draft."))
            # Do not let RPC context defaults bypass the workflow.
            vals["status"] = "draft"
            vals["completed_at"] = False
            vals["reference"] = self.env["ir.sequence"].next_by_code("stocksense.operation") or "New"
        return super().create(vals_list)

    def _lock(self):
        self.check_access("write")
        self.flush_recordset()
        if self.ids:
            self.env.cr.execute("SELECT id FROM stocksense_operation WHERE id IN %s ORDER BY id FOR UPDATE", [tuple(self.ids)])
            self.invalidate_recordset()
        self.check_access("write")

    def _require_draft(self):
        if any(op.status != "draft" for op in self):
            raise UserError(_("Only draft operations can be edited. Reset to Draft first."))

    def write(self, vals):
        self._lock()
        self._require_draft()
        if {"status", "completed_at", "reference"} & vals.keys():
            raise UserError(_("Use the workflow buttons to change an operation's status."))
        return super().write(vals)

    def unlink(self):
        self._lock()
        if any(op.status not in ("draft", "canceled") for op in self):
            raise UserError(_("Only draft or canceled operations can be deleted."))
        return super().unlink()

    def _set_status(self, status):
        values = {"status": status}
        if status == "done":
            values["completed_at"] = fields.Datetime.now()
        return super().write(values)

    def _check_ready(self):
        self.ensure_one()
        self._check_company()
        if not self.line_ids:
            raise ValidationError(_("Add at least one product line."))
        self.line_ids._check_company()
        self.line_ids._check_quantity()
        if any(not line.product_id.active for line in self.line_ids):
            raise ValidationError(_("Archived products cannot be moved."))
        if self.operation_type == "receipt" and (not self.destination_location_id or not self.partner_id):
            raise ValidationError(_("A receipt needs a supplier and destination location."))
        if self.operation_type in ("delivery", "transfer") and not self.source_location_id:
            raise ValidationError(_("Choose a source location."))
        if self.operation_type == "transfer" and (not self.destination_location_id or self.source_location_id == self.destination_location_id):
            raise ValidationError(_("Choose a destination different from the source."))
        if self.operation_type == "adjustment":
            if not self.destination_location_id:
                raise ValidationError(_("Choose the location being counted."))
            if len(self.line_ids.product_id) != len(self.line_ids):
                raise ValidationError(_("Count each product only once in an adjustment."))

    def action_confirm(self):
        self.ensure_one()
        self._lock()
        self._require_draft()
        self._check_ready()
        self._set_status("waiting")
        return True

    def action_ready(self):
        self.ensure_one()
        self._lock()
        if self.status != "waiting":
            raise UserError(_("Only waiting operations can be marked Ready."))
        self._check_ready()
        self._set_status("ready")
        return True

    def action_validate(self):
        self.ensure_one()
        # Savepoint also guarantees all-or-nothing posting if a caller catches
        # the validation exception within a larger transaction.
        with self.env.cr.savepoint():
            self._lock()
            if self.status not in ("draft", "waiting", "ready"):
                raise UserError(_("This operation has already been completed or canceled."))
            self._check_ready()
            service = self.env["stocksense.inventory.service"]
            service._lock_balances(self)
            getattr(self, "_apply_" + self.operation_type)(service)
            self._set_status("done")
        return True

    def action_cancel(self):
        self.ensure_one()
        self._lock()
        if self.status in ("done", "canceled"):
            raise UserError(_("A completed or canceled operation cannot be canceled."))
        self._set_status("canceled")
        return True

    def action_reset_draft(self):
        self.ensure_one()
        self._lock()
        if self.status not in ("waiting", "ready", "canceled"):
            raise UserError(_("This operation cannot be reset to Draft."))
        self._set_status("draft")
        return True


class OperationLine(models.Model):
    _name = "stocksense.operation.line"
    _description = "StockSense Operation Line"
    _check_company_auto = True

    operation_id = fields.Many2one("stocksense.operation", required=True, ondelete="cascade", index=True)
    company_id = fields.Many2one(related="operation_id.company_id", store=True)
    operation_type = fields.Selection(related="operation_id.operation_type")
    product_id = fields.Many2one("stocksense.product", required=True, ondelete="restrict", check_company=True)
    quantity = fields.Float(default=1, digits=(16, 3))
    counted_quantity = fields.Float(string="Physical Count", default=0, digits=(16, 3))
    unit_of_measure = fields.Selection(related="product_id.unit_of_measure")

    @api.constrains("quantity", "counted_quantity", "product_id", "operation_id")
    def _check_quantity(self):
        for line in self:
            value = line.counted_quantity if line.operation_type == "adjustment" else line.quantity
            if not math.isfinite(value) or value < 0 or (line.operation_type != "adjustment" and float_round(value, precision_digits=3) <= 0):
                raise ValidationError(_("Movement quantities must be positive; physical counts may be zero. Use at most three decimal places."))
            if value != float_round(value, precision_digits=3):
                raise ValidationError(_("Quantities support at most three decimal places."))

    @api.model_create_multi
    def create(self, vals_list):
        defaults = self.default_get(["operation_id", "quantity", "counted_quantity"])
        for vals in vals_list:
            for field, value in defaults.items():
                vals.setdefault(field, value)
            self._check_input_numbers(vals)
        operations = self.env["stocksense.operation"].browse([v.get("operation_id") for v in vals_list if v.get("operation_id")])
        operations._lock()
        operations._require_draft()
        return super().create(vals_list)

    def write(self, vals):
        self._check_input_numbers(vals)
        operations = self.operation_id
        operations._lock()
        operations._require_draft()
        if "operation_id" in vals and any(line.operation_id.id != vals["operation_id"] for line in self):
            raise UserError(_("Lines cannot be moved to another operation."))
        return super().write(vals)

    @api.model
    def _check_input_numbers(self, vals):
        # Odoo rounds Float values before constraints run. Reject malformed
        # values before that conversion rather than allowing silent rounding.
        for field in ("quantity", "counted_quantity"):
            if field in vals:
                try:
                    value = float(vals[field])
                except (TypeError, ValueError):
                    raise ValidationError(_("Enter a valid numeric quantity."))
                if not math.isfinite(value) or value < 0 or value != float_round(value, precision_digits=3):
                    raise ValidationError(_("Enter a finite, nonnegative quantity with at most three decimal places."))

    def unlink(self):
        operations = self.operation_id
        operations._lock()
        operations._require_draft()
        return super().unlink()
