import re
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests import HttpCase, tagged
from odoo.tests.common import new_test_user

OTP_SECRETS = "odoo.addons.stocksense.models.password_otp.secrets.randbelow"
DASHBOARD_URL = "/odoo/action-stocksense.action_dashboard"


@tagged("post_install", "-at_install")
class TestAuth(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login="otp_user", email="otp.user@example.com", groups="base.group_user", password="OldPassword1")
        cls.otp = cls.env["stocksense.password.otp"].sudo()

    def issue(self, code=123456):
        with patch(OTP_SECRETS, return_value=code):
            return self.otp._issue("otp.user@example.com")

    def test_valid_code_is_single_use(self):
        self.assertTrue(self.issue())
        self.assertEqual(self.otp._verify("OTP_USER", "123456"), self.user)
        self.assertFalse(self.otp._verify("otp_user", "123456"))

    def test_code_is_stored_hashed(self):
        self.issue()
        record = self.otp.search([("user_id", "=", self.user.id)])
        self.assertNotIn("123456", record.code_hash)

    def test_wrong_codes_lock_the_code(self):
        self.issue()
        for _attempt in range(5):
            self.assertFalse(self.otp._verify("otp_user", "000000"))
        self.assertFalse(self.otp._verify("otp_user", "123456"))

    def test_expired_code_rejected(self):
        self.issue()
        self.otp.search([("user_id", "=", self.user.id)]).write({"expires_at": fields.Datetime.now() - timedelta(seconds=1)})
        self.assertFalse(self.otp._verify("otp_user", "123456"))

    def test_resend_is_throttled_and_replaces_old_code(self):
        self.assertTrue(self.issue(111111))
        self.assertFalse(self.issue(222222))
        self.env.cr.execute("UPDATE stocksense_password_otp SET create_date = create_date - interval '2 minutes' WHERE user_id = %s", [self.user.id])
        self.otp.invalidate_model()
        self.assertTrue(self.issue(333333))
        self.assertFalse(self.otp._verify("otp_user", "111111"))
        self.assertEqual(self.otp._verify("otp_user", "333333"), self.user)

    def test_unknown_login_and_wildcards_do_not_issue(self):
        self.assertFalse(self.otp._issue("nobody@example.com"))
        self.assertFalse(self.otp._issue("otp%"))
        self.assertFalse(self.otp._issue("%"))

    def test_signup_creates_internal_user_landing_on_dashboard(self):
        self.env["res.users"].sudo().signup({"login": "new.staff@example.com", "name": "New Staff", "password": "StaffPass1"})
        user = self.env["res.users"].search([("login", "=", "new.staff@example.com")])
        self.assertTrue(user._is_internal())
        self.assertEqual(user.email, "new.staff@example.com")
        self.assertEqual(user.action_id.id, self.env.ref("stocksense.action_dashboard").id)

    def csrf(self, response):
        return re.search(r'name="csrf_token" value="([^"]+)"', response.text).group(1)

    def test_login_redirects_to_dashboard(self):
        page = self.url_open("/web/login")
        response = self.url_open("/web/login", data={"login": "otp_user", "password": "OldPassword1", "csrf_token": self.csrf(page)}, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].endswith(DASHBOARD_URL))

    def test_reset_password_pages(self):
        page = self.url_open("/web/login")
        self.assertIn("/stocksense/reset_password", page.text)
        page = self.url_open("/stocksense/reset_password")
        with patch(OTP_SECRETS, return_value=654321):
            page = self.url_open("/stocksense/reset_password", data={"login": "otp.user@example.com", "csrf_token": self.csrf(page)})
        self.assertIn("6-digit code", page.text)
        mismatch = self.url_open("/stocksense/reset_password/verify", data={
            "login": "otp.user@example.com", "code": "654321", "password": "NewPassword1",
            "confirm_password": "Different1", "csrf_token": self.csrf(page)})
        self.assertIn("do not match", mismatch.text)
        response = self.url_open("/stocksense/reset_password/verify", data={
            "login": "otp.user@example.com", "code": "654321", "password": "NewPassword1",
            "confirm_password": "NewPassword1", "csrf_token": self.csrf(mismatch)}, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertTrue(response.headers["Location"].endswith(DASHBOARD_URL))
        self.user.invalidate_recordset()
        self.env["res.users"].with_user(self.user)._check_credentials({"type": "password", "password": "NewPassword1"}, {"interactive": False})
