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


class ReportSalePayment(Model):
    _name = "report.sale.payment"
    _transient = True
    _fields = {
        "order_date_from": fields.Date("Order Date From"),
        "order_date_to": fields.Date("Order Date To"),
        "invoice_date_from": fields.Date("Invoice Date From"),
        "invoice_date_to": fields.Date("Invoice Date To"),
        "pay_method_id": fields.Many2One("payment.method", "Payment Method"),
        "account_id": fields.Many2One("account.account", "Account"),
    }
    _defaults = {
        "invoice_date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "invoice_date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

    def get_report_data(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        order_date_from = params.get("order_date_from")
        order_date_to = params.get("order_date_to")
        invoice_date_from = params.get("invoice_date_from")
        invoice_date_to = params.get("invoice_date_to")
        pay_method_id = params.get("pay_method_id")
        account_id = params.get("account_id")
        lines = []
        cond = [["payment_id.state", "=", "posted"], ["type", "=", "invoice"], ["invoice_id.type", "=", "out"]]
        if invoice_date_from:
            cond.append(["invoice_id.date", ">=", invoice_date_from])
        if invoice_date_to:
            cond.append(["invoice_id.date", "<=", invoice_date_to])
        if account_id:
            cond.append(["payment_id.account_id", "=", account_id])
        for pmt_line in get_model("account.payment.line").search_browse(cond, order="payment_id.date,id"):
            pmt = pmt_line.payment_id
            inv = pmt_line.invoice_id
            sale = inv.related_id
            if not sale or sale._model != "sale.order":
                continue
            contact = sale.contact_id
            phone = contact.phone
            for addr in contact.addresses:
                if phone:
                    break
                phone = addr.phone
            line = {
                "order_id": sale.id,
                "order_number": sale.number,
                "invoice_id": inv.id,
                "invoice_number": inv.number,
                "related_id": sale.related_id.id if sale.related_id else None,
                "related_number": sale.related_id.number if sale.related_id.number else None,
                "ref": sale.ref,
                "invoice_date": inv.date,
                "payment_id": pmt.id,
                "payment_date": pmt.date,
                "customer_name": contact.name,
                "phone": phone,
                "pay_method": sale.pay_method_id.name if sale.pay_method_id else "",
                "account_name": pmt.account_id.name,
                "amount": pmt_line.amount,
            }
            lines.append(line)
        data = {
            "company_name": comp.name,
            "order_date_from": order_date_from,
            "order_date_to": order_date_to,
            "invoice_date_from": invoice_date_from,
            "invoice_date_to": invoice_date_to,
            "lines": lines,
            "total": sum(l["amount"] for l in lines),
        }
        data["lines"] = sorted(data["lines"], key=lambda k: (k['pay_method'], k['account_name']))
        total = 0
        pay_method = ""
        account_name = ""
        lines = data["lines"]
        data["lines"] = []
        first = True
        for report_line in lines:
            if (pay_method != report_line["pay_method"] or account_name != report_line["account_name"]) and not first:
                line_vals = {
                    "order_id": "",
                    "order_number": "Account Total",
                    "invoice_id": "",
                    "invoice_number": "",
                    "invoice_date": "",
                    "payment_id": "",
                    "payment_date": "",
                    "customer_name": "",
                    "phone": "",
                    "pay_method": pay_method,
                    "account_name": account_name,
                    "amount": total,
                }
                data["lines"].append(line_vals)
                total = report_line["amount"]
                pay_method = report_line["pay_method"]
                account_name = report_line["account_name"]
            else:
                total += report_line["amount"]
                pay_method = report_line["pay_method"]
                account_name = report_line["account_name"]
            line_vals = {
                "order_id": report_line["order_id"],
                "order_number": report_line["order_number"],
                "invoice_id": report_line["invoice_id"],
                "invoice_number": report_line["invoice_number"],
                "related_id": report_line["related_id"],
                "related_number": report_line["related_number"],
                "ref": report_line["ref"],
                "invoice_date": report_line["invoice_date"],
                "payment_id": report_line["payment_id"],
                "payment_date": report_line["payment_date"],
                "customer_name": report_line["customer_name"],
                "phone": report_line["phone"],
                "pay_method": report_line["pay_method"],
                "account_name": report_line["account_name"],
                "amount": report_line["amount"],
            }
            data["lines"].append(line_vals)
            first = False
        line_vals = {
            "order_id": "",
            "order_number": "Account Total",
            "invoice_id": "",
            "invoice_number": "",
            "invoice_date": "",
            "payment_id": "",
            "payment_date": "",
            "customer_name": "",
            "phone": "",
            "pay_method": pay_method,
            "account_name": account_name,
            "amount": total,
        }
        data["lines"].append(line_vals)

        print(data)
        return data

ReportSalePayment.register()
