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
from netforce.utils import get_file_path


class ReportInvoice(Model):
    _name = "report.invoice"
    _store = False

    def get_data_form(self, context={}):
        inv_id = context.get("invoice_id")  # XXX: old, move this
        if not inv_id:
            inv_id = context["refer_id"]
        inv_id = int(inv_id)
        inv = get_model("account.invoice").browse(inv_id)
        dbname = database.get_active_db()
        company = inv.company_id
        settings = get_model("settings").browse(1)
        comp_addr = settings.get_address_str()
        comp_name = company.name
        comp_phone = settings.phone
        comp_fax = settings.fax
        comp_tax_no = settings.tax_no
        contact = inv.contact_id
        cust_addr = contact.get_address_str()
        cust_name = contact.name
        cust_fax = contact.fax
        cust_phone = contact.phone
        cust_tax_no = contact.tax_no
        data = {
            "comp_name": comp_name,
            "comp_addr": comp_addr,
            "comp_phone": comp_phone or "-",
            "comp_fax": comp_fax or "-",
            "comp_tax_no": comp_tax_no or "-",
            "cust_name": cust_name,
            "cust_addr": cust_addr,
            "cust_phone": cust_phone or "-",
            "cust_fax": cust_fax or "-",
            "cust_tax_no": cust_tax_no or "-",
            "date": inv.date or "-",
            "due_date": inv.due_date or "-",
            "number": inv.number or "-",
            "ref": inv.ref or "-",
            "memo": inv.memo or "",
            "lines": [],
        }
        if settings.logo:
            data["logo"] = get_file_path(settings.logo)
        for line in inv.lines:
            data["lines"].append({
                "description": line.description,
                "code": line.product_id.code,
                "qty": line.qty,
                "uom": line.uom_id.name,
                "unit_price": line.unit_price,
                "discount": line.discount,
                "tax_rate": line.tax_id.rate,
                "amount": line.amount,
            })
        is_cash = 'No'
        is_cheque = 'No'
        for obj in inv.payments:
            account_type = obj.payment_id.account_id.type
            if account_type in ("bank", "cash"):
                is_cash = 'Yes'
            if account_type in ("cheque"):
                is_cheque = 'Yes'
        data.update({
            "amount_subtotal": inv.amount_subtotal,
            "amount_discount": inv.amount_discount,
            "amount_tax": inv.amount_tax,
            "amount_total": inv.amount_total,
            "amount_paid": inv.amount_paid,
            "payment_terms": inv.related_id.payment_terms or "-",
            "is_cash": is_cash,
            "is_cheque": is_cheque,
            "currency_code": inv.currency_id.code,
            "tax_rate": round(inv.amount_tax * 100.0 / inv.amount_subtotal or 0, 2),
            "qty_total": inv.qty_total,
            "memo": inv.memo,
        })
        if inv.credit_alloc:
            data.update({
                "original_inv_subtotal": inv.credit_alloc[0].invoice_id.amount_subtotal,
            })
        return data

    def get_data_contact(self, context={}):
        contact_id = int(context.get("contact_id"))
        date_from = context.get("date_from")
        date_to = context.get("date_to")
        contact = get_model("contact").browse(contact_id)
        condition = []
        if date_from:
            condition.append(["date", ">=", date_from])
        if date_to:
            condition.append(["date", "<=", date_to])
        data = {
            "company_name": context["company_name"],
            "contact_name": contact.name,
            "date_from": date_from,
            "date_to": date_to,
            "lines": [],
            "totals": {
                "amount_total": 0,
                "amount_paid": 0,
                "amount_due": 0,
            },
        }
        invoices = get_model("account.invoice").search_browse(condition)
        for inv in invoices:

            line = {
                "invoice_id": inv.id,
                "date": inv.date,
                "ref": inv.ref,
                "due_date": inv.due_date,
                "amount_total": inv.amount_total,
                "amount_paid": inv.amount_paid,
                "amount_due": inv.amount_due,
            }
            data["lines"].append(line)
            data["totals"]["amount_total"] += inv.amount_total
            data["totals"]["amount_paid"] += inv.amount_paid
            data["totals"]["amount_due"] += inv.amount_due
        return data

    def get_template_invoice_form(self, context={}):
        obj = get_model("account.invoice").browse(int(context["invoice_id"]))
        if obj.type == "out":
            if obj.amount_discount:
                return "cust_invoice_form_disc"
            else:
                return "cust_invoice_form"
        elif obj.type == "in":
            return "supp_invoice_form"

ReportInvoice.register()
