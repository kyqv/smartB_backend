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
from netforce.access import get_active_company
from netforce.database import get_connection
from pprint import pprint


class ReportShipCost(Model):
    _name = "report.ship.cost"
    _transient = True
    _fields = {
        "date_from": fields.Date("From", required=True),
        "date_to": fields.Date("To", required=True),
        "contact_id": fields.Many2One("contact", "Contact"),
        "ship_pay_by": fields.Selection([["company", "Company"], ["customer", "Customer"], ["supplier", "Supplier"]], "Shipping Paid By"),
        "ship_method_id": fields.Many2One("ship.method", "Shipping Method"),
    }
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def get_report_data(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(company_id)
        contact_id = params.get("contact_id")
        cond = [["date", ">=", params["date_from"]], ["date", "<=", params["date_to"]]]
        if params.get("contact_id"):
            cond.append(["contact_id", "=", params["contact_id"]])
        if params.get("ship_pay_by"):
            cond.append(["ship_pay_by", "=", params["ship_pay_by"]])
        if params.get("ship_method_id"):
            cond.append(["ship_method_id", "=", params["ship_method_id"]])
        lines = []
        for pick in get_model("stock.picking").search_browse(cond):
            line = {
                "id": pick.id,
                "date": pick.date,
                "number": pick.number,
                "contact": pick.contact_id.name,
                "ship_method": pick.ship_method_id.name,
                "ship_tracking": pick.ship_tracking,
                "ship_cost": pick.ship_cost,
                "ship_pay_by": pick.ship_pay_by,  # XXX
            }
            try:
                lines["related"] = pick.related_id.name_get()[0][1] if pick.related_id else None
            except:
                pass  # XXX
            lines.append(line)
        totals = {}
        totals["ship_cost"] = sum(l["ship_cost"] or 0 for l in lines)
        data = {
            "company_name": comp.name,
            "date_from": params["date_from"],
            "date_to": params["date_to"],
            "lines": lines,
            "totals": totals,
        }
        return data

ReportShipCost.register()
