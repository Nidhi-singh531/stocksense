from odoo import models, _
from odoo.addons.auth_signup.models.res_partner import SignupError


class ResUsers(models.Model):
    _inherit = "res.users"

    def _create_user_from_template(self, values):
        # Self sign-up creates warehouse staff (internal users). Invitations
        # sent to an existing partner keep Odoo's portal template.
        template = self.env.ref("stocksense.signup_template_user", raise_if_not_found=False)
        if not template or values.get("partner_id"):
            return super()._create_user_from_template(values)
        if not values.get("login") or not values.get("name"):
            raise SignupError(_("Enter your name and email to sign up."))
        values["active"] = True
        try:
            with self.env.cr.savepoint():
                return template.sudo().with_context(no_reset_password=True).copy(values)
        except Exception as error:
            raise SignupError(str(error))
