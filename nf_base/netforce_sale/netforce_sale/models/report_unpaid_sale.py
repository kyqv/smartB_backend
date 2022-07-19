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
from netforce.access import get_active_company


class ReportUnpaidSale(Model):
    _name = "report.unpaid.sale"
    _transient = True
    _fields = {
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
        "pay_method_id": fields.Many2One("payment.method", "Payment Method"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults", {})
        date_from = defaults.get("date_from")
        date_to = defaults.get("date_to")
        if not date_from and not date_to:
            date_from = date.today().strftime("%Y-%m-01")
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        return {
            "date_from": date_from,
            "date_to": date_to,
        }

    def get_report_data(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        date_from = params.get("date_from")
        date_to = params.get("date_to")
        pay_method_id = params.get("pay_method_id")
        lines = []
        cond = [["state", "=", "confirmed"]]
        if date_from:
            cond.append(["date", ">=", date_from])
        if date_to:
            cond.append(["date", "<=", date_to])
        if pay_method_id:
            cond.append(["pay_method_id", "=", pay_method_id])
        for sale in get_model("sale.order").search_browse(cond, order="date,id"):
            if sale.is_paid:
                continue
            contact = sale.contact_id
            phone = contact.phone
            for addr in contact.addresses:
                if phone:
                    break
                phone = addr.phone
            line = {
                "id": sale.id,
                "number": sale.number,
                "related_id": sale.related_id.id if sale.related_id else None,
                "related_number": sale.related_id.number if sale.related_id else None,
                "date": sale.date,
                "customer_name": contact.name,
                "phone": phone,
                "pay_method": sale.pay_method_id.name if sale.pay_method_id else None,
                "amount": sale.amount_total,
            }
            lines.append(line)
        data = {
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
            "lines": lines,
            "total": sum(l["amount"] for l in lines),
        }
        return data

ReportUnpaidSale.register()
