/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const EMPTY_FILTERS = { operation_type: "", status: "", warehouse_id: "", location_id: "", category_id: "" };

export class StockSenseDashboard extends Component {
    static template = "stocksense.Dashboard";
    static props = ["*"];
    static operationTypes = [["receipt", "Receipts"], ["delivery", "Delivery"], ["transfer", "Internal"], ["adjustment", "Adjustments"]];
    static statuses = [["draft", "Draft"], ["waiting", "Waiting"], ["ready", "Ready"], ["done", "Done"], ["canceled", "Canceled"]];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.operationTypes = StockSenseDashboard.operationTypes;
        this.statuses = StockSenseDashboard.statuses;
        this.state = useState({ data: null, loading: false, error: false, filters: { ...EMPTY_FILTERS } });
        onWillStart(() => this.refresh());
    }
    async refresh() {
        this.state.loading = true;
        this.state.error = false;
        try {
            this.state.data = await this.orm.call("stocksense.dashboard", "get_summary", [this.state.filters]);
        } catch {
            this.state.error = true;
        } finally {
            this.state.loading = false;
        }
    }
    get hasFilters() {
        return Object.values(this.state.filters).some(Boolean);
    }
    get locationOptions() {
        const warehouse = Number(this.state.filters.warehouse_id);
        const locations = this.state.data?.options.locations || [];
        return warehouse ? locations.filter((location) => location.warehouse_id === warehouse) : locations;
    }
    isSelected(key, id) {
        return this.state.filters[key] === String(id);
    }
    setFilter(key, value) {
        this.state.filters[key] = value;
        if (key === "warehouse_id" && !this.locationOptions.some((l) => String(l.id) === this.state.filters.location_id)) {
            this.state.filters.location_id = "";
        }
        return this.refresh();
    }
    clearFilters() {
        Object.assign(this.state.filters, EMPTY_FILTERS);
        return this.refresh();
    }
    openAction(name, context = {}) {
        return this.action.doAction(`stocksense.action_${name}`, { additionalContext: context });
    }
    openList(name, model, domain, context = {}) {
        return this.action.doAction({ type: "ir.actions.act_window", name, res_model: model,
            views: [[false, "list"], [false, "form"]], domain, context });
    }
    openPending(type) {
        return this.openList("Pending operations", "stocksense.operation",
            [...this.state.data.pending_domain, ["operation_type", "=", type]], { default_operation_type: type });
    }
    openOperations() {
        return this.openList("Operations", "stocksense.operation", this.state.data.operations_domain);
    }
    openEmpty() {
        return this.openList("Out of stock", "stocksense.product", [["id", "in", this.state.data.empty_product_ids]]);
    }
    openLow() {
        return this.openList("Below reorder minimum", "stocksense.reorder.rule", [["id", "in", this.state.data.low_rule_ids]]);
    }
    openOperation(id) {
        return this.action.doAction({ type: "ir.actions.act_window", res_model: "stocksense.operation",
            res_id: id, views: [[false, "form"]] });
    }
}
registry.category("actions").add("stocksense.dashboard", StockSenseDashboard);
