from odoo import http
from odoo.http import request


class StockSenseDashboard(http.Controller):
    @http.route("/stocksense/dashboard", type="json", auth="user")
    def dashboard(self, filters=None):
        # No sudo: model access and company rules apply to every query.
        return request.env["stocksense.dashboard"].get_summary(filters)
