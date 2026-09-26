from odoo import api, models

PENDING = ["draft", "waiting", "ready"]


class Dashboard(models.AbstractModel):
    _name = "stocksense.dashboard"
    _description = "StockSense Dashboard"

    @api.model
    def _parse_filters(self, filters):
        """Keep only known filter values; anything else is ignored."""
        filters = filters or {}
        operation = self.env["stocksense.operation"]
        parsed = {}
        if filters.get("operation_type") in dict(operation._fields["operation_type"].selection):
            parsed["operation_type"] = filters["operation_type"]
        if filters.get("status") in dict(operation._fields["status"].selection):
            parsed["status"] = filters["status"]
        for key in ("warehouse_id", "location_id", "category_id"):
            try:
                value = int(filters.get(key) or 0)
            except (TypeError, ValueError):
                value = 0
            if value > 0:
                parsed[key] = value
        return parsed

    @api.model
    def _operation_domain(self, filters):
        domain = []
        if filters.get("location_id"):
            location = filters["location_id"]
            domain += ["|", ("source_location_id", "=", location), ("destination_location_id", "=", location)]
        elif filters.get("warehouse_id"):
            warehouse = filters["warehouse_id"]
            domain += ["|", ("source_location_id.warehouse_id", "=", warehouse), ("destination_location_id.warehouse_id", "=", warehouse)]
        if filters.get("category_id"):
            domain.append(("line_ids.product_id.category_id", "=", filters["category_id"]))
        return domain

    @api.model
    def get_summary(self, filters=None):
        filters = self._parse_filters(filters)
        location_domain = []
        if filters.get("location_id"):
            location_domain = [("location_id", "=", filters["location_id"])]
        elif filters.get("warehouse_id"):
            location_domain = [("location_id.warehouse_id", "=", filters["warehouse_id"])]
        product_domain = [("category_id", "=", filters["category_id"])] if filters.get("category_id") else []

        products = self.env["stocksense.product"].search(product_domain)
        stock = self.env["stocksense.stock"].search([("product_id", "in", products.ids)] + location_domain)
        totals = dict.fromkeys(products.ids, 0.0)
        balances = {}
        for balance in stock:
            totals[balance.product_id.id] += balance.quantity
            balances[(balance.product_id.id, balance.location_id.id)] = balance.quantity
        empty = [product_id for product_id, quantity in totals.items() if quantity <= 0]
        low = []
        rules = self.env["stocksense.reorder.rule"].search([("product_id", "in", products.ids)] + location_domain)
        for rule in rules:
            quantity = balances.get((rule.product_id.id, rule.location_id.id), 0)
            if quantity < rule.minimum_quantity:
                low.append({"id": rule.id, "product": rule.product_id.display_name,
                            "location": rule.location_id.display_name, "quantity": quantity,
                            "minimum": rule.minimum_quantity,
                            "suggested": max(0, rule.target_quantity - quantity)})

        operations = self.env["stocksense.operation"]
        scope = self._operation_domain(filters)
        pending = scope + [("status", "in", PENDING)]
        listed = list(scope)
        if filters.get("operation_type"):
            listed.append(("operation_type", "=", filters["operation_type"]))
        if filters.get("status"):
            listed.append(("status", "=", filters["status"]))
        recent = operations.search(listed, limit=8)

        warehouses = self.env["stocksense.warehouse"].search([])
        return {
            "filters": filters,
            "products": len(products), "out_of_stock": len(empty), "empty_product_ids": empty,
            "low_stock": len(low), "low_items": low[:12], "low_rule_ids": [item["id"] for item in low],
            "receipts": operations.search_count(pending + [("operation_type", "=", "receipt")]),
            "deliveries": operations.search_count(pending + [("operation_type", "=", "delivery")]),
            "transfers": operations.search_count(pending + [("operation_type", "=", "transfer")]),
            "adjustments": operations.search_count(pending + [("operation_type", "=", "adjustment")]),
            "operations_domain": listed, "operations_count": operations.search_count(listed),
            "pending_domain": pending,
            "recent": [{"id": op.id, "reference": op.reference, "type": op.operation_type,
                        "status": op.status, "date": str(op.date)} for op in recent],
            "options": {
                "warehouses": [{"id": w.id, "name": w.display_name} for w in warehouses],
                "locations": [{"id": l.id, "name": l.display_name, "warehouse_id": l.warehouse_id.id}
                              for l in self.env["stocksense.location"].search([])],
                "categories": [{"id": c.id, "name": c.display_name}
                               for c in self.env["stocksense.product.category"].search([])],
            },
        }
