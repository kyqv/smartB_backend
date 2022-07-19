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
from netforce.access import get_active_user, set_active_user
import re


def check_password(p):
    if len(p) < 5:
        raise Exception("Password must be at least 5 characters")
    if not re.search("\d", p):
        raise Exception("Password must contain at least 1 digit")
    if not re.search("[A-Z]", p):
        raise Exception("Password must contain at least 1 uppercase letter")
    if not re.search("[a-z]", p):
        raise Exception("Password must contain at least 1 lowercase letter")
    return True


class UserPref(Model):
    _name = "user.pref"
    _transient = True
    _fields = {
        "name": fields.Char("Name", required=True),
        "password": fields.Char("Password", required=True),
        "email": fields.Char("Email"),
        "mobile": fields.Char("Mobile"),
    }

    def default_get(self, field_names=None, context=None, **kw):
        user_id = get_active_user()
        set_active_user(1)
        user = get_model("base.user").browse(user_id)
        vals = {
            "name": user.name,
            "password": user.password,
            "email": user.email,
            "mobile": user.mobile,
        }
        set_active_user(user_id)
        return vals

    def save_changes(self, ids, context={}):
        obj = self.browse(ids)[0]
        #raise Exception("pass: %s"%obj.password)
        #check_password(obj.password)
        vals = {
            "name": obj.name,
            "password": obj.password,
            "email": obj.email,
            "mobile": obj.mobile,
        }
        user_id = get_active_user()
        set_active_user(1)
        get_model("base.user").write([user_id], vals)
        #obj.write({"password": "****"})
        set_active_user(user_id)
        return {
            "alert": "Changes saved successfully.",
        }

UserPref.register()
