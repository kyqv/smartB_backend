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
from netforce import utils
from datetime import *
from dateutil.relativedelta import *
from netforce import database
from netforce.access import get_active_company
from pprint import pprint


class ReportTaxMonth(Model):
    _name = "report.tax.month"
    _transient = True
    _fields = {
        "date_from": fields.Date("From",required=True),
        "date_to": fields.Date("To",required=True),
        "tax_type": fields.Selection([["vat", "VAT"], ["vat_exempt", "VAT Exempt"], ["vat_defer", "Deferred VAT"], ["wht", "Withholding Tax"]], "Tax Type"),
        "trans_type": fields.Selection([["out", "Sale"], ["in", "Purchase"]], "Transaction Type"),
        "contact_type": fields.Selection([["company", "Company"], ["individual", "Individual"]], "Contact Type"),
    }

    def default_get(self, field_names=None, context={}, **kw):
        defaults = context.get("defaults", {})
        date_from = defaults.get("date_from")
        if not date_from:
            date_from = date.today().strftime("%Y-%m-01")
        date_to = defaults.get("date_to")
        if not date_to:
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        return {
            "date_from": date_from,
            "date_to": date_to,
            "trans_type": "out",
        }

    def get_report_data(self, ids=None, context={}):
        print("ReportTaxMonth.get_report_data",ids,context)
        company_id = get_active_company()
        company_ids = get_model("company").search([["id", "child_of", company_id]])
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        date_from = params.get("date_from")
        if not date_from:
            date_from = date.today().strftime("%Y-%m-01")
        date_to = params.get("date_to")
        if not date_to:
            date_to = (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        tax_type=params.get("tax_type")
        trans_type=params.get("trans_type")
        contact_type=params.get("contact_type")
        data={
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
        }
        cond=[["move_id.state","=","posted"], ["or",["move_id.date",">=",date_from],["tax_date",">=",date_from]],["or",["move_id.date","<=",date_to],["tax_date","<=",date_to]],["move_id.company_id","in",company_ids]]
        if tax_type:
            cond.append(["tax_comp_id.type","=",tax_type])
        if trans_type:
            cond.append(["tax_comp_id.trans_type","=",trans_type])
        if contact_type:
            cond.append(["tax_comp_id.contact_type","=",contact_type])
        lines=[]
        for line in get_model("account.move.line").search_browse(cond,order="move_id.date,move_id.number"):
            move=line.move_id
            inv=move.related_id if move.related_id and move.related_id._model=="account.invoice" else None
            if inv:
                contact=inv.contact_id
            else:
                contact=line.contact_id
            sign=1
            if inv and inv.inv_type=="credit": # XXX
                sign=-1
            if inv:
                inv_no=inv.number
            else:
                inv_no=line.tax_no
            tax_date=line.tax_date or move.date
            if tax_date<date_from:
                continue
            if tax_date>date_to:
                continue
            vals={
                "move_id": move.id,
                "date": utils.format_date(tax_date),
                "invoice_date": utils.format_date(tax_date),
                #"invoice_date": utils.format_date(inv.date) if inv else None,
                "invoice_id": inv.id if inv else None,
                "invoice_currency": inv.currency_id.code if inv else None,
                "invoice_subtotal": inv.amount_subtotal if inv else None,
                "invoice_tax": inv.amount_tax if inv else None,
                "print_form_no": inv.print_form_no if inv else None,
                "tax_comp_name": line.tax_comp_id.name,
                "invoice_no": inv_no,
                "contact_name": contact.name if contact else None,
                "contact_code": contact.code if contact else None,
                "contact_tax_id": contact.tax_no if contact else None,
                "contact_branch": contact.branch if contact else None,
                "base_amount": line.tax_base*sign,
                "tax_amount": abs(line.debit-line.credit)*sign,
                "comments": inv.remarks if inv else None,
            }
            vals["amount"]=vals["base_amount"]+vals["tax_amount"]
            lines.append(vals)
            #if move.id==878:
            #    raise Exception("XXXY")
        data["lines"]=[]
        """
        inv_lines={}
        for vals in lines:
            k=(vals["invoice_no"],vals["date"])
            if k in inv_lines:
                inv_line=inv_lines[k]
                inv_line["base_amount"]+=vals["base_amount"]
                inv_line["tax_amount"]+=vals["tax_amount"]
            else:
                inv_line=vals.copy()
                data["lines"].append(inv_line)
                inv_lines[k]=inv_line
        """
        for vals in lines:
            inv_line=vals.copy()
            data["lines"].append(inv_line)
        data["lines"].sort(key=lambda l: l["date"] or "")
        data["base_total"]=sum(l["base_amount"] for l in data["lines"]) if data["lines"] else 0
        data["tax_total"]=sum(l["tax_amount"] for l in data["lines"]) if data["lines"] else 0
        data["amount_total"]=sum(l["amount"] for l in data["lines"]) if data["lines"] else 0
        #pprint(data)
        return data

ReportTaxMonth.register()
