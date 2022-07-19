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
from netforce.utils import get_data_path
import time
import uuid


class ConvertLead(Model):
    _name = "convert.lead"
    _transient = True
    _fields = {
        "lead_id": fields.Many2One("sale.lead", "Lead", required=True, on_delete="cascade"),
        "user_id": fields.Many2One("base.user", "Assigned To", required=True, on_delete="cascade"),
        "contact_id": fields.Many2One("contact", "Contact", required=True, on_delete="cascade"),
        "name": fields.Char("Opportunity Name", required=True),
        "uuid": fields.Char("UUID"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults")
        if defaults:
            lead_id = int(defaults["lead_id"])
            lead = get_model("sale.lead").browse(lead_id)
            res = get_model("contact").search([["name", "=", lead.company]])
            if res:
                defaults["contact_id"] = res[0]
            defaults["user_id"] = lead.user_id.id
        return super().default_get(field_names, context, **kw)

    def do_copy(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "user_id": obj.user_id.id,
            "name": obj.name,
            "contact_id": obj.contact_id.id,
        }
        opp_id = get_model("sale.opportunity").create(vals)
        return {
            "next": {
                "name": "opport",
                "mode": "form",
                "active_id": opp_id,
            }
        }

ConvertLead.register()
