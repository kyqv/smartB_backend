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
from datetime import *
from dateutil.relativedelta import *
from netforce import database
from netforce import access

class Report(Model):
    _name = "report.track.budget"
    _transient=True
    _fields = {
        "track_id": fields.Many2One("account.track.categ","Tracking"),
        "contact_id": fields.Many2One("contact","Supplier"),
    }
    _defaults={
    }

    def get_report_data(self, ids, context={}):
        company_id = access.get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        track_id=params.get("track_id")
        contact_id=params.get("contact_id")
        if not track_id and not contact_id:
            return
        cond=[]
        if track_id:
            cond.append(["track_id","=",track_id])
        if contact_id:
            cond.append(["contact_id","=",contact_id])
        lines=[]
        for line in get_model("account.budget.line").search_browse(cond):
            vals={
                "contact_name": line.contact_id.name,
                "contact_id": line.contact_id.id,
                "account_name": line.account_id.name,
                "account_code": line.account_id.code,
                "account_id": line.account_id.id,
                "budget_amount": line.budget_amount,
                "actual_amount": line.actual_amount,
                "paid_amount": line.paid_amount,
                "unpaid_amount": line.unpaid_amount,
            }
            lines.append(vals)
        track=get_model("account.track.categ").browse(track_id) if track_id else None
        contact=get_model("contact").browse(contact_id) if contact_id else None
        data={
            "company_name": comp.name,
            "track_code": track.code if track else None,
            "track_name": track.name if track else None,
            "track_id": track.id if track else None,
            "contact_name": contact.name if contact else None,
            "lines": lines,
            "budget_total": sum(l["budget_amount"] for l in lines),
            "actual_total": sum(l["actual_amount"] for l in lines),
            "paid_total": sum(l["paid_amount"] or 0 for l in lines),
            "unpaid_total": sum(l["unpaid_amount"] or 0 for l in lines),
        }
        return data

Report.register()
