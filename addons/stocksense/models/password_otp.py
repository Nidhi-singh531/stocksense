import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from markupsafe import Markup
from odoo import api, fields, models, _
from odoo.tools import config
from odoo.tools.sql import escape_psql

_logger = logging.getLogger(__name__)

CODE_LIFETIME = timedelta(minutes=10)
RESEND_DELAY = timedelta(seconds=60)
MAX_ATTEMPTS = 5


class PasswordOtp(models.Model):
    _name = "stocksense.password.otp"
    _description = "StockSense Password Reset Code"
    _order = "id desc"

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade", index=True)
    code_hash = fields.Char(required=True)
    expires_at = fields.Datetime(required=True)
    attempts = fields.Integer(default=0)
    used = fields.Boolean(default=False)

    # These methods run from public routes and must be called on sudo().
    @api.model
    def _find_user(self, login):
        login = escape_psql((login or "").strip())
        if not login:
            return self.env["res.users"]
        users = self.env["res.users"].search(["|", ("login", "=ilike", login), ("email", "=ilike", login)], limit=2)
        # An ambiguous email must not pick an account at random.
        return users if len(users) == 1 else self.env["res.users"]

    @api.model
    def _hash(self, user, code):
        secret = self.env["ir.config_parameter"].get_param("database.secret")
        return hmac.new(secret.encode(), f"{user.id}:{code}".encode(), hashlib.sha256).hexdigest()

    @api.model
    def _issue(self, login):
        """Email a new code. Silent when no account matches, so the page never
        reveals which logins exist."""
        user = self._find_user(login)
        if not user or not user.email:
            return False
        latest = self.search([("user_id", "=", user.id)], limit=1)
        if latest and latest.create_date > fields.Datetime.now() - RESEND_DELAY:
            return False
        self.search([("user_id", "=", user.id), ("used", "=", False)]).write({"used": True})
        code = f"{secrets.randbelow(10**6):06d}"
        self.create({"user_id": user.id, "code_hash": self._hash(user, code),
                     "expires_at": fields.Datetime.now() + CODE_LIFETIME})
        body = Markup(
            "<p>Hello %s,</p><p>Your StockSense password reset code is:</p>"
            "<p style='font-size:28px;font-weight:bold;letter-spacing:6px'>%s</p>"
            "<p>It expires in 10 minutes. If you did not ask to reset your password, ignore this email.</p>"
        ) % (user.name, code)
        mail = self.env["mail.mail"].create({
            "subject": _("Your StockSense password reset code"),
            "email_from": self.env["ir.mail_server"]._get_default_from_address() or user.company_id.email_formatted or user.email_formatted,
            "email_to": user.email_formatted, "body_html": body, "auto_delete": True,
        })
        mail.send(raise_exception=False)
        if mail.exists() and mail.state == "exception":
            _logger.warning("StockSense could not email a password reset code to user %s: %s", user.id, mail.failure_reason)
            if config["dev_mode"]:
                # Local development without an outgoing mail server.
                _logger.warning("Developer mode: password reset code for %s is %s", user.login, code)
        return True

    @api.model
    def _verify(self, login, code):
        """Consume a valid code and return its user, or an empty recordset."""
        user = self._find_user(login)
        if not user:
            return self.env["res.users"]
        otp = self.search([("user_id", "=", user.id), ("used", "=", False),
                           ("expires_at", ">", fields.Datetime.now())], limit=1)
        if not otp:
            return self.env["res.users"]
        # Serialize attempts so parallel guesses cannot exceed the limit.
        self.env.cr.execute("SELECT id FROM stocksense_password_otp WHERE id = %s FOR UPDATE", [otp.id])
        otp.invalidate_recordset()
        if otp.used or otp.attempts >= MAX_ATTEMPTS:
            return self.env["res.users"]
        if not hmac.compare_digest(otp.code_hash, self._hash(user, (code or "").strip())):
            otp.write({"attempts": otp.attempts + 1, "used": otp.attempts + 1 >= MAX_ATTEMPTS})
            return self.env["res.users"]
        otp.write({"used": True})
        return user

    @api.autovacuum
    def _gc_expired_codes(self):
        self.search([("expires_at", "<", fields.Datetime.now() - timedelta(days=1))]).unlink()
