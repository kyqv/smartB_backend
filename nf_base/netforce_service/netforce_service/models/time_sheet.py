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
import time
from netforce.access import get_active_user
import datetime
from netforce.utils import get_data_path


class TimeSheet(Model):
    _name = "time.sheet"
    _string = "Time Sheet"
    _fields = {
        "employee_id": fields.Many2One("hr.employee", "Employee", search=True),  # XXX: deprecated
        "resource_id": fields.Many2One("service.resource", "Resource", required=True, search=True, on_delete="cascade"),
        "date": fields.Date("Date", required=True, search=True),
        "state": fields.Selection([["draft", "Draft"], ["waiting_approval", "Waiting Approval"], ["approved", "Approved"], ["rejected", "Rejected"]], "Status", required=True, search=True),
        "work_time": fields.One2Many("work.time", "timesheet_id", "Work Time"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
    }
    _order = "date,employee_id"

    def get_employee(self, context={}):
        user_id = get_active_user()
        res = get_model("hr.employee").search([["user_id", "=", user_id]])
        if not res:
            return None
        return res[0]

    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "employee_id": get_employee,
        "state": "draft",
    }

    def submit(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"state": "waiting_approval"})
        obj.trigger("submit"),

    def approve(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"state": "approved"})
        obj.trigger("approve"),

    def reject(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"state": "rejected"})
        obj.trigger("reject"),

    def to_draft(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"state": "draft"})

    def write(self, ids, vals, **kw):
        super().write(ids, vals, **kw)
        for obj in self.browse(ids):
            for t in obj.work_time:
                t.write({
                    "date": obj.date,
                    "employee_id": obj.employee_id.id,
                })

    def onchange_product(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        product_id = line["product_id"]
        prod = get_model("product").browse(product_id)
        line["description"] = prod.description
        line["unit_price"] = prod.cost_price
        return data

TimeSheet.register()
