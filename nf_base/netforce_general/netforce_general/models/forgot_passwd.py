# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce.model import Model, fields, get_model
from random import choice
import string
from netforce import access


class ForgotPasswd(Model):
    _name = "forgot.passwd"
    _transient = True
    _fields = {
        "email": fields.Char("Enter your email:", required=True),
        "key": fields.Char("Key"),
    }

    def create(self, vals, **kw):
        uid = access.get_active_user()
        try:
            access.set_active_user(1)
            return super().create(vals, **kw)
        finally:
            access.set_active_user(uid)

    def default_get(self, field_names=None, context={}, **kw):
        chars = string.ascii_letters + string.digits
        length = 8
        key = ''.join([choice(chars) for _ in range(length)])
        return {
            "key": key
        }

    def send_email(self, ids, context={}):
        uid = access.get_active_user()
        try:
            access.set_active_user(1)
            obj = self.browse(ids[0])
            # XXX "=" should be changed to "=ilike" later
            res = get_model("base.user").search((["email", "=ilike", obj.email.strip()]))
            if not res:
                raise Exception("User with given email doesn't exist in database")
            request = context["request"]
            msg = "Somebody requested change of your Netforce password.\n\n"
            msg += "If you didn't do it, please ignore this message.\n\n"
            msg += "Otherwise if you want to reset your password click on the link below:\n\n"
            msg += "http://%s/ui#name=change_passwd&key=%s\n\n\n" % (request.host, obj.key)
            msg += "Regards,\n"
            msg += "Netforce Team"
            vals = {
                "type": "out",
                "from_addr": "support@netforce.com",
                "to_addrs": obj.email,
                "subject": "Netforce reset password request",
                "body": msg,
                "state": "to_send",
            }
            get_model("email.message").create(vals)
            return {
                "next": {
                    "name": "forgot_passwd_done"
                }
            }
        finally:
            access.set_active_user(uid)

ForgotPasswd.register()
