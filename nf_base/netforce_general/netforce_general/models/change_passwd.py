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


class ChangePasswd(Model):
    _name = "change.passwd"
    _transient = True
    _fields = {
        "key": fields.Char("Key", required=True),
        "new_password": fields.Char("Enter new password:", required=True),
        "new_password_repeat": fields.Char("Confirm new password:", required=True),
    }

    def default_get(self, field_names=None, context={}, **kw):
        key = context['key']
        return {
            "key": key
        }

    def change_passwd(self, ids, context={}):
        change_passwd = self.browse(ids)[0]
        res = get_model("forgot.passwd").search([["key", "=", change_passwd.key]])
        if not res:
            raise Exception("Invalid key")
        forgot_passwd = get_model("forgot.passwd").browse(res[0])
        res = get_model("base.user").search([["email", "=", forgot_passwd.email]])
        if not res:
            raise Exception("Invalid email")
        user_id = res[0]
        new_password = change_passwd.new_password
        if len(change_passwd.new_password) < 4:
            raise Exception("Password has to be at least 4 characters long")
        new_password_repeat = change_passwd.new_password_repeat
        if new_password != new_password_repeat:
            raise Exception("Passwords are not matching")
        get_model("base.user").write([user_id], {"password": new_password})
        return {
            "next": {
                "name": "login"
            },
            "flash": "Your password has been changed"
        }

ChangePasswd.register()
