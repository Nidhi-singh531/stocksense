from urllib.parse import urlsplit

from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from odoo.addons.web.controllers.utils import ensure_db, is_user_internal

DASHBOARD_URL = "/odoo/action-stocksense.action_dashboard"


class StockSenseHome(Home):
    def _login_redirect(self, uid, redirect=None):
        # Land on the dashboard unless the user was heading somewhere specific.
        generic = not redirect or (urlsplit(redirect).path.rstrip("/") in ("/odoo", "/web") and not urlsplit(redirect).query.strip("?"))
        if generic and request.session.uid and is_user_internal(uid):
            redirect = DASHBOARD_URL
        return super()._login_redirect(uid, redirect=redirect)


class StockSensePasswordReset(http.Controller):
    @http.route("/stocksense/reset_password", type="http", auth="public", methods=["GET", "POST"], sitemap=False)
    def reset_request(self, login="", **kw):
        ensure_db()
        login = (login or "").strip()
        if request.httprequest.method == "POST" and login:
            request.env["stocksense.password.otp"].sudo()._issue(login)
            return request.render("stocksense.reset_password_verify", {
                "login": login,
                "message": _("If an account matches, we emailed it a 6-digit code. The code expires in 10 minutes."),
            })
        return request.render("stocksense.reset_password_request", {"login": login})

    @http.route("/stocksense/reset_password/verify", type="http", auth="public", methods=["POST"], sitemap=False)
    def reset_verify(self, login="", code="", password="", confirm_password="", **kw):
        ensure_db()
        login = (login or "").strip()
        values = {"login": login}
        if len(password or "") < 8:
            values["error"] = _("Use a password with at least 8 characters.")
        elif password != confirm_password:
            values["error"] = _("The passwords do not match.")
        else:
            user = request.env["stocksense.password.otp"].sudo()._verify(login, code)
            if not user:
                values["error"] = _("That code is invalid or has expired. Request a new code.")
            else:
                user.write({"password": password})
                request.env.cr.commit()  # authenticate() uses a new cursor
                request.session.authenticate(request.db, {"login": user.login, "password": password, "type": "password"})
                return request.redirect(DASHBOARD_URL)
        return request.render("stocksense.reset_password_verify", values)
