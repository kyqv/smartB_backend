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

from netforce.model import Model, fields
from netforce.access import get_active_user
import json


class FieldDefault(Model):
    _name = "field.default"
    _string = "Field Default"
    _fields = {
        "user_id": fields.Many2One("base.user", "User", required=True, search=True),
        "model": fields.Char("Model", required=True, search=True),
        "field": fields.Char("Field", required=True, search=True),
        "value": fields.Text("Value"),
    }

    def set_default(self, model, field, value, context={}):
        self.clear_default(model, field)
        user_id = get_active_user()
        vals = {
            "user_id": user_id,
            "model": model,
            "field": field,
            "value": value,
        }
        self.create(vals)

    def clear_default(self, model, field, context={}):
        user_id = get_active_user()
        res = self.search([["user_id", "=", user_id], ["model", "=", model], ["field", "=", field]])
        if res:
            self.delete(res)

    def get_default(self, model, field, context={}):
        user_id = get_active_user()
        res = self.search([["user_id", "=", user_id], ["model", "=", model], ["field", "=", field]])
        if not res:
            return None
        obj_id = res[0]
        obj = self.browse(obj_id)
        return obj.value

FieldDefault.register()
