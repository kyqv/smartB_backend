# Copyright (c) 2012-2017 Netforce Software Co. Ltd.
# All Rights Reserved.
#
# This file is part of Netforce
# (see https://netforce.com/).

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
        data={
            "company_name": comp.name,
            "date_from": date_from,
            "date_to": date_to,
        }
        cond=[["move_id.state","=","posted"], ["move_id.date",">=",date_from],["move_id.date","<=",date_to]]
        if tax_type:
            cond.append(["tax_comp_id.type","=",tax_type])
        if trans_type:
            cond.append(["tax_comp_id.trans_type","=",trans_type])
        lines=[]
        for line in get_model("account.move.line").search_browse(cond,order="move_id.number,move_id.date,move_id"):
            move=line.move_id
            inv=move.related_id if move.related_id and move.related_id._model=="account.invoice" else None
            sign=1
            if trans_type=="out":
                if line.debit:
                    sign=-1
            elif trans_type=="in":
                if line.credit:
                    sign=-1
            vals={
                "date": utils.format_date(move.date),
                "invoice_date": utils.format_date(inv.date) if inv else None,
                "invoice_id": inv.id if inv else None,
                "print_form_no": inv.print_form_no if inv else None,
                "tax_comp_name": line.tax_comp_id.name,
                "invoice_no": inv.number if inv else None,
                "contact_name": inv.contact_id.name if inv else None,
                "contact_tax_id": inv.contact_id.tax_no if inv else None,
                "contact_branch": inv.contact_id.branch if inv else None,
                "base_amount": line.tax_base*sign,
                "tax_amount": (line.credit-line.debit)*sign,
                "comments": inv.remarks if inv else None,
            }
            vals["amount"]=vals["base_amount"]+vals["tax_amount"]
            lines.append(vals)
        data["lines"]=[]
        inv_lines={}
        for vals in lines:
            inv_id=vals["invoice_id"]
            if inv_id in inv_lines:
                inv_line=inv_lines[inv_id]
                inv_line["base_amount"]+=vals["base_amount"]
                inv_line["tax_amount"]+=vals["tax_amount"]
            else:
                inv_line=vals.copy()
                data["lines"].append(inv_line)
                inv_lines[inv_id]=inv_line
        data["base_total"]=sum(l["base_amount"] for l in data["lines"]) if data["lines"] else 0
        data["tax_total"]=sum(l["tax_amount"] for l in data["lines"]) if data["lines"] else 0
        data["amount_total"]=sum(l["amount"] for l in data["lines"]) if data["lines"] else 0
        #pprint(data)
        return data

ReportTaxMonth.register()
