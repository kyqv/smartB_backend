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
from netforce.utils import get_data_path, set_data_path, get_file_path, json_dumps
from pprint import pprint
from netforce.access import get_active_company
from netforce import access
from decimal import *
from netforce import tasks, utils
import json
from datetime import *
import time

class Payment(Model):
    _name = "account.payment"
    _name_field = "number"
    _string = "Payment"
    _multi_company = True
    _audit_log = True
    _key = ["company_id", "number"]
    _content_search=True
    _fields = {
        "type": fields.Selection([["out", "Paid"], ["in", "Received"]], "Payment Type", required=True, search=True),
        "pay_type": fields.Selection([["direct", "Direct Payment"], ["invoice", "Invoice Payment"]], "Payment Subtype", required=True, search=True),
        "contact_id": fields.Many2One("contact", "Contact", search=True),
        "date": fields.Date("Date", required=True, search=True),
        "ref": fields.Char("Ref", search=True, size=256),  # not used any more
        "memo": fields.Char("Memo", search=True, size=256),
        "tax_type": fields.Selection([["tax_ex", "Tax Exclusive"], ["tax_in", "Tax Inclusive"], ["no_tax", "No Tax"]], "Tax Type", required=True),
        "account_id": fields.Many2One("account.account", "Payment Account", search=True),
        "currency_id": fields.Many2One("currency", "Currency", required=True, search=True),
        "lines": fields.One2Many("account.payment.line", "payment_id", "Lines"),
        "direct_lines": fields.One2Many("account.payment.line", "payment_id", "Direct Payments", condition=[["type", "=", "direct"]]),
        "invoice_lines": fields.One2Many("account.payment.line", "payment_id", "Invoice Payments", condition=[["type", "=", "invoice"]]),
        "invlines": fields.One2Many("account.payment.line", "payment_id", "Invoice Payments", condition=[["type", "=", "invoice"]]), # XXX: testing, remove this
        "prepay_lines": fields.One2Many("account.payment.line", "payment_id", "Prepayments", condition=[["type", "=", "prepay"]]),
        "overpay_lines": fields.One2Many("account.payment.line", "payment_id", "Overpayments", condition=[["type", "=", "overpay"]]),
        "claim_lines": fields.One2Many("account.payment.line", "payment_id", "Claim Payments", condition=[["type", "=", "claim"]]),
        "adjust_lines": fields.One2Many("account.payment.line", "payment_id", "Adjustments", condition=[["type", "=", "adjust"]]),
        "amount_subtotal": fields.Decimal("Subtotal", function="get_amount", function_multi=True, store=True),
        "amount_tax": fields.Decimal("Tax Amount", function="get_amount", function_multi=True, store=True),
        "amount_total": fields.Decimal("Total", function="get_amount", function_multi=True, store=True),
        "amount_total_words": fields.Char("Total Words", function="get_amount_total_words", store=False),
        "amount_wht": fields.Decimal("Withholding Tax", function="get_amount", function_multi=True, store=True),
        "amount_wht_base": fields.Decimal("Withholding Tax Base Amount", function="get_amount", function_multi=True, store=True),
        "amount_payment": fields.Decimal("Net Payment Amount", function="get_amount", function_multi=True, store=True),
        "amount_adjust": fields.Decimal("Adjustment Amount", function="get_amount", function_multi=True, store=True),
        "move_id": fields.Many2One("account.move", "Journal Entry"),
        "currency_rate": fields.Decimal("Currency Rate (Pmt->Com)", scale=6),
        "state": fields.Selection([["draft", "Draft"], ["posted", "Posted"], ["voided", "Voided"]], "State", required=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "number": fields.Char("Number", required=True, search=True),
        "default_line_desc": fields.Boolean("Default memo to line description"),
        "company_id": fields.Many2One("company", "Company"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "tax_no": fields.Char("Tax No"),
        "wht_no": fields.Char("WHT No", search=True),
        "related_id": fields.Reference([["sale.order", "Sales Order"], ["purchase.order", "Purchase Order"], ["project", "Project"], ["job", "Service Order"], ["service.contract", "Service Contract"],["ecom.cart","Cart"],["hr.payrun","Pay Run"]], "Related To"),
        "employee_id": fields.Many2One("hr.employee", "Employee"),
        "credit_invoices": fields.One2Many("account.invoice", "payment_id", "Credit Invoices"),
        "journal_id": fields.Many2One("account.journal", "Journal"),
        "sequence_id": fields.Many2One("sequence", "Number Sequence"),
        "transaction_no": fields.Char("Transaction ID",search=True),
        "pay_method_id": fields.Many2One("payment.method", "Payment Method"),
        "cheque_number": fields.Char("Cheque Number",function="get_cheque",function_multi=True),
        "cheque_bank": fields.Char("Cheque Bank",function="get_cheque",function_multi=True),
        "cheque_branch": fields.Char("Cheque Branch",function="get_cheque",function_multi=True),
        "cheque_date": fields.Date("Cheque Date",function="get_cheque",function_multi=True),
        "cheques": fields.One2Many("account.cheque","related_id","Cheques"),
        "image": fields.File("Picture"),
        "wht_cert_pages": fields.Json("WHT Cert Pages",function="get_wht_cert_pages"),
        "user_id": fields.Many2One("base.user", "Owner", search=True),
        "track_id": fields.Many2One("account.track.categ", "Tracking"),
        "amount_change": fields.Decimal("Change Amount"),
        "date_week": fields.Char("Week",function="get_date_agg",function_multi=True),
        "date_month": fields.Char("Month",function="get_date_agg",function_multi=True),
    }
    _order = "date desc, number desc, id desc"

    def _get_currency(self, context={}):
        settings = get_model("settings").browse(1)
        return settings.currency_id.id

    def _get_number(self, context={}):
        type = context.get("type")
        if not type:
            st_line_id=context.get("statement_line_id")
            if st_line_id:
                line=get_model("account.statement.line").browse(st_line_id)
                if line.spent:
                    type="out"
                elif line.received:
                    type="in"
        seq_id = context.get("sequence_id")
        if not seq_id:
            if type == "in":
                seq_type = "pay_in"
            elif type == "out":
                seq_type = "pay_out"
            else:
                return
            seq_id = get_model("sequence").find_sequence(type=seq_type)
            if not seq_id:
                return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    def _get_date(self,context):
        st_line_id=context.get("statement_line_id")
        if st_line_id:
            line=get_model("account.statement.line").browse(st_line_id)
            return line.date[:10]
        return time.strftime("%Y-%m-%d")

    def _get_account(self,context):
        st_line_id=context.get("statement_line_id")
        if st_line_id:
            line=get_model("account.statement.line").browse(st_line_id)
            return line.statement_id.account_id.id

    def _get_memo(self,context):
        st_line_id=context.get("statement_line_id")
        if st_line_id:
            line=get_model("account.statement.line").browse(st_line_id)
            m="From statement: "
            if line.received:
                m+="received %s"%line.received
            elif line.spent:
                m+="spent %s"%line.spent
            if line.description:
                m+=" (%s)"%line.description
            return m

    def _get_type(self,context):
        st_line_id=context.get("statement_line_id")
        if st_line_id:
            line=get_model("account.statement.line").browse(st_line_id)
            type=None
            if line.received:
                type="in"
            if line.spent:
                type="out"
            return type

    _defaults = {
        "date": _get_date,
        "tax_type": "tax_ex",
        "currency_id": _get_currency,
        "number": _get_number,
        "state": "draft",
        "pay_type": "direct",
        "company_id": lambda *a: get_active_company(),
        "default_line_desc": True,
        "account_id": _get_account,
        "memo": _get_memo,
        "type": _get_type,
        "user_id": lambda *a: access.get_active_user(),
    }
    #_constraints=["check_empty"] # XXX: in myob, payment can be empty...

    def check_empty(self, ids, context={}):
        for obj in self.browse(ids):
            if not obj.lines:
                raise Exception("Payment is empty")

    def create(self, vals, **kw):
        new_id = super().create(vals, **kw)
        self.function_store([new_id])
        return new_id

    def write(self, ids, vals, **kw):
        invoice_ids = []
        expense_ids = []
        for obj in self.browse(ids):
            for line in obj.lines:
                if line.invoice_id:
                    invoice_ids.append(line.invoice_id.id)
                if line.expense_id:
                    expense_ids.append(line.expense_id.id)
        super(Payment, self).write(ids, vals, **kw)
        self.function_store(ids)
        invoice_id = vals.get("invoice_id")
        if invoice_id:
            invoice_ids.append(invoice_id)
        expense_id = vals.get("expense_id")
        if expense_id:
            expense_ids.append(expense_id)
        if invoice_ids:
            get_model("account.invoice").function_store(invoice_ids)
        if expense_ids:
            get_model("expense.claim").function_store(expense_ids)

    def delete(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.state == "posted":
                raise Exception("Can't delete posted payments")
        super().delete(ids)

    def void(self, ids, context={}):
        invoice_ids = []
        expense_ids = []
        for obj in self.browse(ids):
            obj.write({"state": "voided"})
            obj.delete_credit_invoices()
            if obj.move_id:
                obj.move_id.void()
                obj.move_id.delete()
            for line in obj.lines:
                if line.invoice_id:
                    invoice_ids.append(line.invoice_id.id)
                if line.expense_id:
                    expense_ids.append(line.expense_id.id)
        if invoice_ids:
            get_model("account.invoice").function_store(invoice_ids)
        if expense_ids:
            get_model("expense.claim").function_store(expense_ids)

    def to_draft(self, ids, context={}):
        invoice_ids = []
        expense_ids = []
        for obj in self.browse(ids):
            obj.write({"state": "draft"})
            obj.delete_credit_invoices()
            if obj.move_id:
                obj.move_id.void()
                obj.move_id.delete()
            for line in obj.lines:
                if line.invoice_id:
                    invoice_ids.append(line.invoice_id.id)
                if line.expense_id:
                    expense_ids.append(line.expense_id.id)
        if invoice_ids:
            get_model("account.invoice").function_store(invoice_ids)
        if expense_ids:
            get_model("expense.claim").function_store(expense_ids)

    def do_delete(self, ids, context={}):
        obj = self.browse(ids)[0]
        account_id = obj.account_id.id
        if obj.move_id:
            obj.move_id.delete()
        obj.delete()
        return {
            "next": {
                "name": "bank_transactions",
                "account_id": account_id,
            },
            "flash": "Payment deleted",
        }

    def get_amount_total_words(self, ids, context={}): #Pang copied from purchase.order 3 Nov 2020
        vals = {}
        for obj in self.browse(ids):
            amt=obj.amount_total or 0
            words=utils.num2words(int(amt)).upper()
            cents=int(amt*100)%100
            if cents:
                word_cents=utils.num2words(cents).upper()
                cents_name=obj.currency_id.cents_name or "CENTS"
                words+=" AND %s %s"%(word_cents,cents_name)
            vals[obj.id]=words
        return vals
 
    def get_amount(self, ids, context={}):
        settings = get_model("settings").browse(1)
        res = {}
        for obj in self.browse(ids):
            vals = {}
            subtotal = 0
            vat = 0
            total = 0
            wht = 0
            wht_base = 0
            for line in obj.lines:
                if line.type=="direct" and obj.pay_type!="direct":
                    continue
                if line.type in ("invoice","adjust") and obj.pay_type!="invoice":
                    continue
                if line.type in ("direct", "prepay", "overpay", "adjust"):
                    line_amt=line.amount
                    line_vat = 0
                    line_wht = 0
                    line_wht_base = 0
                    if line.tax_id:
                        tax=line.tax_id
                        base_amt = get_model("account.tax.rate").compute_base(
                            tax.id, line_amt, tax_type=obj.tax_type)
                        tax_comps = get_model("account.tax.rate").compute_taxes(
                            tax.id, base_amt, when="direct_payment")
                        for comp_id, tax_amt in tax_comps.items():
                            comp = get_model("account.tax.component").browse(comp_id)
                            if comp.type == "vat":
                                line_vat += tax_amt
                            elif comp.type == "wht":
                                line_wht -= tax_amt
                                line_wht_base += base_amt
                    vat += line_vat
                    wht += line_wht
                    wht_base += line_wht_base
                    if obj.tax_type == "tax_in":
                        subtotal += line_amt - line_vat
                    else:
                        subtotal += line_amt
                    total+=line_amt
                elif line.type=="invoice":
                    inv = line.invoice_id
                    cred_amt = 0
                    inv_vat = 0
                    inv_wht = 0
                    inv_wht_base = 0
                    if inv:
                        for alloc in inv.credit_notes:
                            cred_amt += alloc.amount
                        if inv.inv_type in ("invoice", "credit", "debit"):
                            pay_ratio = line.amount / (inv.amount_total - cred_amt)  # XXX: check this again
                            for invline in inv.lines:
                                invline_amt = invline.amount * pay_ratio
                                tax = invline.tax_id
                                if tax and inv.tax_type != "no_tax":
                                    base_amt = get_model("account.tax.rate").compute_base(
                                        tax.id, invline_amt, tax_type=inv.tax_type)
                                    # TODO: remove this later (use.inv.taxes)
                                    tax_comps = get_model("account.tax.rate").compute_taxes(
                                        tax.id, base_amt, when="direct_payment")
                                    for comp_id, tax_amt in tax_comps.items():
                                        comp = get_model("account.tax.component").browse(comp_id)
                                        if comp.type == "vat":
                                            inv_vat += tax_amt
                                        elif comp.type == "wht":
                                            inv_wht -= tax_amt
                                            inv_wht_base+=base_amt
                                else:
                                    base_amt = invline_amt
                                subtotal += base_amt
                            #if inv.taxes: # FIXME!!! (WHT)
                            if False:
                                inv_vat = 0
                                inv_wht = 0
                                for tax in inv.taxes:
                                    comp=tax.tax_comp_id
                                    tax_amt=tax.tax_amount*pay_ratio
                                    if comp.type == "vat":
                                        inv_vat += tax_amt
                                    elif comp.type == "wht":
                                        inv_wht -= tax_amt
                            for alloc in inv.credit_notes:
                                cred = alloc.credit_id
                                cred_ratio = alloc.amount / cred.amount_total
                                for credline in cred.lines:
                                    credline_amt = credline.amount * cred_ratio * pay_ratio  # XXX: check this again
                                    tax = credline.tax_id
                                    if tax and cred.tax_type != "no_tax":
                                        base_amt = get_model("account.tax.rate").compute_base(
                                            tax.id, credline_amt, tax_type=cred.tax_type)
                                        # TODO: make this more clear...
                                        tax_comps = get_model("account.tax.rate").compute_taxes(
                                            tax.id, base_amt, when="direct_payment")
                                        for comp_id, tax_amt in tax_comps.items():
                                            comp = get_model("account.tax.component").browse(comp_id)
                                            if comp.type == "vat":
                                                inv_vat -= tax_amt
                                            elif comp.type == "wht":
                                                inv_wht += tax_amt
                                    else:
                                        base_amt = credline_amt
                                    subtotal -= base_amt
                        elif inv.inv_type == "overpay":
                            subtotal += line.amount
                    inv_vat = get_model("currency").round(obj.currency_id.id, inv_vat)
                    inv_wht = get_model("currency").round(obj.currency_id.id, inv_wht)
                    vat += inv_vat
                    wht += inv_wht
                    wht_base += inv_wht_base
                    total += line.amount
                elif line.type == "claim":  # XXX
                    subtotal += line.amount
                    total += line.amount
            vat = get_model("currency").round(obj.currency_id.id, vat)
            wht = get_model("currency").round(obj.currency_id.id, wht)
            wht_base = get_model("currency").round(obj.currency_id.id, wht_base)
            vals["amount_subtotal"] = subtotal
            vals["amount_tax"] = vat
            vals["amount_total"] = subtotal + vat
            vals["amount_wht"] = wht
            vals["amount_wht_base"] = wht_base
            vals["amount_payment"] = vals["amount_total"] - wht
            vals["amount_adjust"]=sum(l.amount or 0 for l in obj.adjust_lines)
            res[obj.id] = vals
        return res

    def onchange_amount_invoice(self,context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        amount_inv = line.get("amount_invoice") or 0
        if data["type"] == "in":
            rate_type = "sell"
        else:
            rate_type = "buy"
        inv_id=line["invoice_id"]
        if not inv_id:
            return
        inv = get_model("account.invoice").browse(inv_id)
        if line["currency_rate"]:
            rate=Decimal(1)/line["currency_rate"]
        else:
            rate=None
        line["amount"] = get_model("currency").convert(amount_inv, inv.currency_id.id, data["currency_id"], date=data["date"], rate_type=rate_type, rate=rate)
        return self.update_amounts(context)

    def onchange_amount_payment(self,context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        amount_pmt = line.get("amount") or 0
        if data["type"] == "in":
            rate_type = "sell"
        else:
            rate_type = "buy"
        inv_id=line["invoice_id"]
        if not inv_id:
            return
        inv = get_model("account.invoice").browse(inv_id)
        line["amount_invoice"] = get_model("currency").convert(amount_pmt, data["currency_id"], inv.currency_id.id, date=data["date"], rate_type=rate_type, rate=line["currency_rate"])
        return self.update_amounts(context)

    def update_amounts(self, context):
        settings = get_model("settings").browse(1)
        data = context["data"]
        pay_type = data["pay_type"]
        tax_type = data["tax_type"]
        currency_id = data["currency_id"]
        subtotal = 0
        vat = 0
        wht = 0
        if pay_type == "direct":
            for line in data["direct_lines"]:
                if not line:
                    continue
                if line.get("unit_price") is not None:
                    amt = line.get("qty", 0) * line.get("unit_price", 0)
                    line["amount"] = amt
                else:
                    amt = line.get("amount", 0)
                tax_id = line.get("tax_id")
                if tax_id:
                    line_vat = get_model("account.tax.rate").compute_tax(tax_id, amt, tax_type=tax_type)
                    line_wht = get_model("account.tax.rate").compute_tax(tax_id, amt, tax_type=tax_type, wht=True)
                else:
                    line_vat = 0
                    line_wht = 0
                if tax_type == "tax_in":
                    subtotal += amt - line_vat
                else:
                    subtotal += amt
                vat += line_vat
                wht += line_wht
        elif pay_type == "invoice":
            for line in data["invoice_lines"]:
                if not line:
                    continue
                inv_id = line["invoice_id"]
                inv = get_model("account.invoice").browse(inv_id)
                inv_vat = 0
                if inv.inv_type in ("invoice", "credit", "debit"):
                    pay_ratio = line["amount"] / inv.amount_total
                    for invline in inv.lines:
                        invline_amt = invline.amount * pay_ratio
                        tax = invline.tax_id
                        if tax and inv.tax_type != "no_tax":
                            base_amt = get_model("account.tax.rate").compute_base(
                                tax.id, invline_amt, tax_type=inv.tax_type)
                            # TODO: make this more clear...
                            tax_comps = get_model("account.tax.rate").compute_taxes(
                                tax.id, base_amt, when="direct_payment")
                            for comp_id, tax_amt in tax_comps.items():
                                comp = get_model("account.tax.component").browse(comp_id)
                                if comp.type == "vat":
                                    inv_vat += tax_amt
                                elif comp.type == "wht":
                                    wht -= tax_amt
                        else:
                            base_amt = invline_amt
                        subtotal += base_amt
                inv_vat = get_model("currency").round(currency_id, inv_vat)
                vat += inv_vat
            for line in data.get("adjust_lines",[]):
                if not line:
                    continue
                if line["amount_company"]:
                    if data["type"] == "in":
                        rate_type = "sell"
                    else:
                        rate_type = "buy"
                    if data["currency_rate"]:
                        rate=Decimal(1)/data["currency_rate"]
                    else:
                        rate=None
                    conv_amt = get_model("currency").convert(line["amount_company"], settings.currency_id.id, data["currency_id"], rate=rate)
                    line["amount"]=conv_amt
        elif pay_type == "prepay":
            for line in data["prepay_lines"]:
                if not line:
                    continue
                if line.get("unit_price") is not None:
                    amt = line.get("qty", 0) * line.get("unit_price", 0)
                    line["amount"] = amt
                else:
                    amt = line.get("amount", 0)
                tax_id = line.get("tax_id")
                if tax_id:
                    line_vat = get_model("account.tax.rate").compute_tax(tax_id, amt, tax_type=tax_type)
                    line_wht = get_model("account.tax.rate").compute_tax(tax_id, amt, tax_type=tax_type, wht=True)
                else:
                    line_vat = 0
                    line_wht = 0
                if tax_type == "tax_in":
                    subtotal += amt - line_vat
                else:
                    subtotal += amt
                vat += line_vat
                wht += line_wht
        vat = get_model("currency").round(currency_id, vat)
        wht = get_model("currency").round(currency_id, wht)
        data["amount_subtotal"] = subtotal
        data["amount_tax"] = vat
        data["amount_total"] = subtotal + vat
        data["amount_wht"] = wht
        data["amount_payment"] = data["amount_total"] - wht
        return data

    def post_check_overpay(self, ids, context={}):
        obj = self.browse(ids)[0]
        if obj.pay_type == "invoice":
            for line in obj.invoice_lines:
                inv = line.invoice_id
                amt = inv.amount_due
                if inv.type == "out" and obj.type == "out" or inv.type == "in" and obj.type == "in":
                    amt = -amt
                line_amt=(line.amount_invoice or line.amount)
                if line_amt>amt:
                    raise Exception("Payment amount is over invoice due amount (%s > %s, %s)."%(line_amt,amt,inv.number))
        obj.post()

    def post(self, ids, context={}):
        print("account_payment.post")
        settings = get_model("settings").browse(1)
        job_id=context.get("job_id")
        for i,obj in enumerate(self.browse(ids)):
            access.set_active_company(obj.company_id.id)
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*100/len(ids),"Posting payment %s of %s."%(i+1,len(ids)))
            if not obj.account_id:
                raise Exception("Missing account")
            if obj.currency_rate:
                currency_rate = obj.currency_rate
            else:
                if obj.currency_id.id == settings.currency_id.id:
                    currency_rate = 1.0
                else:
                    rate_from = obj.currency_id.get_rate(date=obj.date)
                    if not rate_from:
                        raise Exception("Missing currency rate for %s" % obj.currency_id.code)
                    rate_to = settings.currency_id.get_rate(date=obj.date)
                    if not rate_to:
                        raise Exception("Missing currency rate for %s" % settings.currency_id.code)
                    currency_rate = rate_from / (rate_to or 1)
                obj.write({"currency_rate": currency_rate})
            if obj.pay_type == "direct":
                desc = obj.memo or obj.ref or obj.contact_id.name or obj.number  # XXX: as in myob?
            elif obj.pay_type == "invoice":
                desc = obj.memo or "Payment; %s" % obj.contact_id.name  # XXX: as in myob?
            elif obj.pay_type == "prepay":
                desc = "Prepayment: %s" % obj.contact_id.name
            elif obj.pay_type == "overpay":
                desc = "Overpayment: %s" % obj.contact_id.name
            elif obj.pay_type == "claim":
                desc = "Expense claim payment"
            elif obj.pay_type == "adjust":
                desc = "Adjustment"
            else:
                desc = "Payment: %s" % obj.contact_id.name
            if obj.type == "in":
                journal_id = obj.journal_id.id or settings.pay_in_journal_id.id
                if not journal_id:
                    raise Exception("Receipts journal not found")
            elif obj.type == "out":
                journal_id = obj.journal_id.id or settings.pay_out_journal_id.id
                if not journal_id:
                    raise Exception("Disbursements journal not found")
            if not obj.number:
                raise Exception("Missing payment number")
            move_vals = {
                "journal_id": journal_id,
                "number": obj.number,
                "date": obj.date,
                "narration": desc,
                "related_id": "account.payment,%s" % obj.id,
                "company_id": obj.company_id.id,
                "track_id": obj.track_id.id,
            }
            move_id = get_model("account.move").create(move_vals)
            lines = []
            amt = get_model("currency").convert(
                obj.amount_payment, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
            if obj.type == "out":
                amt = -amt
            if not obj.account_id:
                raise Exception("Missing account in payment %s"%obj.number)
            line_vals = {
                "move_id": move_id,
                "account_id": obj.account_id.id,
                "track_id": obj.track_id.id,
                "description": desc,
                "debit": amt > 0 and amt or 0,
                "credit": amt < 0 and -amt or 0,
            }
            if obj.account_id.currency_id.id != settings.currency_id.id:
                if obj.account_id.currency_id.id != obj.currency_id.id:
                    raise Exception("Invalid account currency for this payment: %s" % obj.account_id.code)
                line_vals["amount_cur"] = obj.amount_payment
            get_model("account.move.line").create(line_vals)
            taxes = {}
            reconcile_ids = []
            total_over = 0
            for line in obj.lines:
                if line.type=="direct":
                    if obj.pay_type!="direct":
                        continue
                    cur_amt = get_model("currency").convert(
                        line.amount, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
                    contact_id=line.contact_id.id or obj.contact_id.id
                    tax_no=line.tax_no or obj.tax_no
                    tax_date=line.tax_date
                    tax = line.tax_id
                    if tax and obj.tax_type != "no_tax":
                        base_amt = get_model("account.tax.rate").compute_base(tax.id, cur_amt, tax_type=obj.tax_type)
                        tax_comps = get_model("account.tax.rate").compute_taxes(tax.id, base_amt, when="direct_payment")
                        for comp_id, tax_amt in tax_comps.items():
                            k=(comp_id,contact_id,tax_no,tax_date)
                            if k in taxes:
                                tax_vals = taxes[k]
                                tax_vals["amount_base"] += base_amt
                                tax_vals["amount_tax"] += tax_amt
                            else:
                                tax_vals = {
                                    "tax_comp_id": comp_id,
                                    "amount_base": base_amt,
                                    "amount_tax": tax_amt,
                                }
                                taxes[k] = tax_vals
                    else:
                        base_amt = cur_amt
                    if obj.type == "out":
                        amt = base_amt
                    else:
                        amt = -base_amt
                    if not line.account_id:
                        raise Exception("Missing account in payment line (%s)"%obj.number)
                    line_desc=line.description or desc
                    if obj.memo:
                        line_desc=obj.memo+" "+line_desc
                    line_vals = {
                        "move_id": move_id,
                        "description": line_desc,
                        "account_id": line.account_id.id,
                        "debit": amt > 0 and amt or 0,
                        "credit": amt < 0 and -amt or 0,
                        "track_id": line.track_id.id,
                        "track2_id": line.track2_id.id,
                        "contact_id": contact_id,
                    }
                    if line.type=="prepay":
                        line_vals["contact_id"]=obj.contact_id.id
                    print("direct")
                    #pprint(line_vals)
                    get_model("account.move.line").create(line_vals)
                elif line.type=="invoice":
                    if obj.pay_type!="invoice":
                        continue
                    inv = line.invoice_id
                    inv_taxes = {}
                    if inv.inv_type in ("invoice", "credit", "debit"):
                        if not inv.account_id:
                            raise Exception("Missing account in invoice (%s)"%inv.number)
                        line_vals = {
                            "move_id": move_id,
                            "description": desc,
                            "account_id": inv.account_id.id,
                            "due_date": inv.due_date,
                            "contact_id": inv.contact_id.id,
                        }
                        inv_pay_amt = line.amount_invoice or line.amount
                        if obj.type==inv.type:
                            inv_pay_amt = -inv_pay_amt
                        if inv.inv_type=="credit":
                            inv_pay_amt=-inv_pay_amt
                            max_pay_amt=-inv.amount_due
                        else:
                            max_pay_amt=inv.amount_due
                        if inv_pay_amt > max_pay_amt:
                            inv_pay_amt = max_pay_amt
                            over_amt = inv_pay_amt - max_pay_amt
                            total_over += get_model("currency").convert(over_amt, inv.currency_id.id,
                                                                        settings.currency_id.id, rate=inv.currency_rate)
                        pay_ratio = inv_pay_amt / inv.amount_total
                        if not inv.move_id or not inv.move_id.lines:
                            raise Exception("Missing journal entry for invoice %s"%inv.number)
                        cur_inv_amt=abs(inv.move_id.lines[0].debit-inv.move_id.lines[0].credit)*pay_ratio # to avoid rounding issue (in invoice convert currency separately for each line)

                        if inv.type == "in":
                            amt = cur_inv_amt
                        else:
                            amt = -cur_inv_amt
                        if inv.inv_type=="credit":
                            amt=-amt
                        if amt > 0:
                            line_vals["debit"] = amt
                        else:
                            line_vals["credit"] = -amt
                        if inv.account_id.currency_id.id != settings.currency_id.id:
                            line_vals["amount_cur"] = inv_pay_amt
                        print("invoice")
                        #pprint(line_vals)
                        pay_line_id = get_model("account.move.line").create(line_vals)
                        if inv.reconcile_move_line_id:
                            inv_line_id = inv.reconcile_move_line_id.id
                        elif inv.move_id:  # XXX
                            inv_line_id = inv.move_id.lines[0].id
                        else:
                            inv_line_id = None
                        if inv_line_id:
                            reconcile_ids.append([pay_line_id, inv_line_id])
                        for invline in inv.lines:
                            tax = invline.tax_id
                            if tax and inv.tax_type != "no_tax":  # XXX: simplify this
                                cur_line_amt_inv = get_model("currency").convert(
                                    invline.amount * pay_ratio, inv.currency_id.id, settings.currency_id.id, rate=inv.currency_rate)
                                base_amt = get_model("account.tax.rate").compute_base(
                                    tax.id, cur_line_amt_inv, tax_type=inv.tax_type)
                                tax_comps = get_model("account.tax.rate").compute_taxes(
                                    tax.id, base_amt, when="invoice_payment_inv")
                                for comp_id, tax_amt in tax_comps.items():
                                    tax_no=inv.tax_no or inv.number
                                    if comp_id in inv_taxes:
                                        tax_vals = inv_taxes[comp_id]
                                        tax_vals["amount_base"] += base_amt
                                        tax_vals["amount_tax"] += tax_amt
                                    else:
                                        tax_vals = {
                                            "tax_comp_id": comp_id,
                                            "amount_base": base_amt,
                                            "amount_tax": tax_amt,
                                        }
                                        inv_taxes[comp_id] = tax_vals
                                cur_line_amt_pmt = get_model("currency").convert(
                                    invline.amount * pay_ratio, inv.currency_id.id, settings.currency_id.id, rate=inv.currency_rate)  # XXX: check this
                                base_amt = get_model("account.tax.rate").compute_base(
                                    tax.id, cur_line_amt_pmt, tax_type=inv.tax_type)
                                tax_comps = get_model("account.tax.rate").compute_taxes(
                                    tax.id, base_amt, when="invoice_payment_pmt")
                                for comp_id, tax_amt in tax_comps.items():
                                    if comp_id in inv_taxes:
                                        tax_vals = inv_taxes[comp_id]
                                        tax_vals["amount_base"] += base_amt
                                        tax_vals["amount_tax"] += tax_amt
                                    else:
                                        tax_vals = {
                                            "tax_comp_id": comp_id,
                                            "amount_base": base_amt,
                                            "amount_tax": tax_amt,
                                        }
                                        inv_taxes[comp_id] = tax_vals
                    for comp_id, inv_tax_vals in inv_taxes.items():
                        comp = get_model("account.tax.component").browse(comp_id)
                        if comp.type in ("vat", "vat_defer"):
                            acc_id = comp.account_id.id
                            if not acc_id:
                                raise Exception("Missing account for tax component %s" % comp.name)
                            line_vals = {
                                "move_id": move_id,
                                "description": desc,
                                "account_id": acc_id,
                                "tax_comp_id": comp_id,
                                "tax_base": inv_tax_vals["amount_base"],
                                "contact_id": obj.contact_id.id,
                                "invoice_id": inv.id,
                                "tax_no": inv.tax_no or inv.number,
                            }
                            """
                            if comp.type == "vat":
                                if inv.type == "out":
                                    if line.tax_no:
                                        tax_no = line.tax_no
                                    else:
                                        tax_no = get_model("account.invoice").gen_tax_no(context={"date": obj.date})
                                        line.write({"tax_no": tax_no})
                                    line_vals["tax_no"] = tax_no
                                elif inv.type == "in":
                                    line_vals["tax_no"] = line.tax_no
                            """
                            amt = inv_tax_vals["amount_tax"]
                            if obj.type == "in":
                                amt = -amt
                            if amt > 0:
                                line_vals["debit"] = amt
                            else:
                                line_vals["credit"] = -amt
                            print("tax")
                            #pprint(line_vals)
                            get_model("account.move.line").create(line_vals)
                        elif comp.type == "wht":
                            k=(comp.id,inv.contact_id.id,inv.tax_no or inv.number,inv.date)
                            if k in taxes:
                                tax_vals = taxes[k]
                                tax_vals["amount_base"] += inv_tax_vals["amount_base"]
                                tax_vals["amount_tax"] += inv_tax_vals["amount_tax"]
                            else:
                                taxes[k] = inv_tax_vals.copy()
                elif line.type == "adjust":
                    if obj.pay_type!="invoice":
                        continue
                    if line.amount_company:
                        cur_amt=line.amount_company
                    else:
                        cur_amt = get_model("currency").convert(
                            line.amount, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
                    tax_base = get_model("currency").convert(
                        line.tax_base or 0, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
                    if not line.account_id:
                        raise Exception("Missing account in payment adjust line (%s)"%obj.number)
                    line_vals = {
                        "move_id": move_id,
                        "description": line.description or desc,
                        "account_id": line.account_id.id,
                        "tax_comp_id": line.tax_comp_id.id,
                        "tax_base": tax_base,
                        "track_id": line.track_id.id,
                        "contact_id": obj.contact_id.id,
                    }
                    if obj.type == "in":
                        cur_amt = -cur_amt
                    if cur_amt > 0:
                        line_vals["debit"] = cur_amt
                    else:
                        line_vals["credit"] = -cur_amt
                    print("adjust")
                    #pprint(line_vals)
                    get_model("account.move.line").create(line_vals)
            if total_over > 0:
                contact = obj.contact_id
                if obj.type == "in":
                    account_id = contact.account_receivable_id.id or settings.account_receivable_id.id
                    if not account_id:
                        raise Exception("Account receivable not found")
                elif obj.type == "out":
                    account_id = contact.account_payable_id.id or settings.account_payable_id.id
                    if not account_id:
                        raise Exception("Account payable not found")
                line_vals = {
                    "move_id": move_id,
                    "description": context.get("overpay_description", ""),
                    "account_id": account_id,
                    "track_id": line.track_id.id,
                    "contact_id": obj.contact_id.id,
                }
                if obj.type == "out":
                    line_vals["debit"] = total_over
                else:
                    line_vals["credit"] = total_over
                print("overpay")
                #pprint(line_vals)
                get_model("account.move.line").create(line_vals)
                inv_line_vals = {
                    "description": context.get("overpay_description", ""),
                    "account_id": account_id,
                    "amount": total_over,
                }
                inv_vals = {
                    "type": obj.type == "in" and "out" or "in",
                    "inv_type": "overpay",
                    "contact_id": obj.contact_id.id,
                    "date": obj.date,
                    "tax_type": "no_tax",
                    "lines": [("create", inv_line_vals)],
                    "state": "waiting_payment",
                    "payment_id": obj.id,
                    "account_id": account_id,
                }
                inv_id = get_model("account.invoice").create(inv_vals)
            #for (comp_id,contact_id,tax_no,tax_date), tax_vals in sorted(taxes.items()):
            for (comp_id,contact_id,tax_no,tax_date), tax_vals in taxes.items():
                comp = get_model("account.tax.component").browse(comp_id)
                acc_id = comp.account_id.id
                if not acc_id:
                    raise Exception("Missing account for tax component %s" % comp.name)
                line_vals = {
                    "move_id": move_id,
                    "description": desc,
                    "account_id": acc_id,
                    "tax_comp_id": comp_id,
                    "tax_base": tax_vals["amount_base"],
                    "contact_id": contact_id,
                    "tax_no": tax_no,
                    "tax_date": tax_date,
                }
                """ TODO: check this
                if comp.type == "vat":
                    if obj.type == "in":
                        if obj.tax_no:
                            tax_no = obj.tax_no
                        else:
                            tax_no = get_model("account.invoice").gen_tax_no(context={"date": obj.date})
                            obj.write({"tax_no": tax_no})
                        line_vals["tax_no"] = tax_no
                    elif obj.type == "out":
                        line_vals["tax_no"] = obj.tax_no
                elif comp.type == "wht":
                    if obj.type == "out":
                        if obj.wht_no:
                            wht_no=obj.wht_no
                        else:
                            wht_no = get_model("account.payment").gen_wht_no(context={"date": obj.date})
                            obj.write({"wht_no":wht_no})
                        line_vals["tax_no"] = wht_no
                """
                amt = tax_vals["amount_tax"]
                if obj.type == "in":
                    amt = -amt
                if amt > 0:
                    line_vals["debit"] = amt
                else:
                    line_vals["credit"] = -amt
                print("tax")
                #pprint(line_vals)
                get_model("account.move.line").create(line_vals)
            amt = 0
            move = get_model("account.move").browse(move_id)
            for line in move.lines:
                amt += line.credit - line.debit
            if amt > 0:
                if not settings.currency_loss_id:
                    raise Exception("Missing currency loss account")
                line_vals = {
                    "move_id": move_id,
                    "description": desc,
                    "account_id": settings.currency_loss_id.id,
                    "debit": amt,
                    "credit": 0,
                }
                get_model("account.move.line").create(line_vals)
            elif amt < 0:
                if not settings.currency_gain_id:
                    raise Exception("Missing currency gain account")
                line_vals = {
                    "move_id": move_id,
                    "description": desc,
                    "account_id": settings.currency_gain_id.id,
                    "debit": 0,
                    "credit": -amt,
                }
                get_model("account.move.line").create(line_vals)
            get_model("account.move").post([move_id])
            obj.write({"move_id": move_id, "state": "posted"})
            for rec_lines in reconcile_ids:
                get_model("account.move.line").reconcile(rec_lines)
            obj.create_prepay_invoice()

    def post_async(self, ids, context={}):
        user_id=access.get_active_user()
        company_id=access.get_active_company()
        vals={
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "account.payment",
            "method": "post",
            "user_id": user_id,
            "company_id": company_id,
            "args": json.dumps({
                "ids": ids,
            }),
        }
        get_model("bg.task").create(vals)

    def create_prepay_invoice(self, ids, context={}):
        obj = self.browse(ids)[0]
        if obj.pay_type == "prepay":
            vals = {
                "number": obj.number,
                "type": obj.type == "in" and "out" or "in",
                "inv_type": "prepay",
                "contact_id": obj.contact_id.id,
                "date": obj.date,
                "tax_type": obj.tax_type,
                "lines": [],
                "state": "waiting_payment",
                "payment_id": obj.id,
                "currency_id": obj.currency_id.id,
            }
            for line in obj.lines:
                line_vals = {
                    "description": line.description,
                    "qty": line.qty,
                    "unit_price": line.unit_price,
                    "account_id": line.account_id.id,
                    "tax_id": line.tax_id.id,
                    "amount": line.amount,
                }
                vals["lines"].append(("create", line_vals))
            inv_id = get_model("account.invoice").create(vals,context={"type":vals["type"],"inv_type":"prepay"})
        elif obj.pay_type == "invoice":
            for line in obj.lines:
                if line.type != "invoice":
                    continue
                inv = line.invoice_id
                pp_lines = []
                for inv_line in inv.lines:
                    acc = inv_line.account_id
                    if acc.type == "cust_deposit":
                        pp_line_vals = {
                            "product_id": inv_line.product_id.id,
                            "description": inv_line.description,
                            "qty": inv_line.qty,
                            "unit_price": inv_line.unit_price,
                            "account_id": inv_line.account_id.id,
                            "tax_id": inv_line.tax_id.id,
                            "amount": inv_line.amount,
                        }
                        pp_lines.append(pp_line_vals)
                if pp_lines:
                    vals = {
                        "type": inv.type,
                        "inv_type": "prepay",
                        "contact_id": inv.contact_id.id,
                        "date": obj.date,
                        "tax_type": inv.tax_type,
                        "lines": [("create", l) for l in pp_lines],
                        "state": "waiting_payment",
                        "payment_id": obj.id,
                        "currency_id": obj.currency_id.id,
                    }
                    inv_id = get_model("account.invoice").create(vals,context={"type":vals["type"],"inv_type":"prepay"})

    def delete_credit_invoices(self, ids, context={}):  # XXX: improve/simplify this
        obj = self.browse(ids)[0]
        for inv in obj.credit_invoices:
            inv.void()
            inv.delete()

    def onchange_account(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        acc_id = line.get("account_id")
        if not acc_id:
            return {}
        acc = get_model("account.account").browse(acc_id)
        line["tax_id"] = acc.tax_id.id
        data = self.update_amounts(context)
        if data.get("default_line_desc"):
            if not line.get("description"):
                line["description"]=data.get("memo")
        return data

    def onchange_invoice(self, context):
        data = context["data"]
        path = context["path"]
        pay_type = data["type"]
        line = get_data_path(data, path, parent=True)
        inv_id = line.get("invoice_id")
        if not inv_id:
            return {}
        inv = get_model("account.invoice").browse(inv_id)
        line["account_id"] = inv.account_id.id
        amt = inv.amount_due
        if inv.type == "out" and pay_type == "out" or inv.type == "in" and pay_type == "in":
            amt = -amt
        line["amount"] = amt
        data = self.update_amounts(context)
        return data

    def onchange_payment(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        claim_id = line.get("claim_id")
        if not claim_id:
            return {}
        claim = get_model("account.claim").browse(claim_id)
        line["amount"] = claim.amount_due
        data = self.update_amounts(context)
        return data

    def repost_payments(self, context={}):  # XXX
        ids = self.search([["state", "=", "posted"]], order="date")
        for obj in self.browse(ids):
            print("payment %d..." % obj.id)
            if not obj.move_id:
                raise Exception("No journal entry for payment #%d" % obj.id)
            obj.move_id.delete()
            obj.post(context={"no_copy": True})

    def copy(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "contact_id": obj.contact_id.id,
            "type": obj.type,
            "pay_type": obj.pay_type,
            "account_id": obj.account_id.id,
            "date": obj.date,
            "currency_id": obj.currency_id.id,
            "tax_type": obj.tax_type,
            "memo": obj.memo,
            "default_line_desc": obj.default_line_desc,
        }
        lines = []
        for line in obj.lines:
            line_vals = {
                "type": line.type,
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "unit_price": line.unit_price,
                "account_id": line.account_id.id,
                "tax_id": line.tax_id.id,
                "track_id": line.track_id.id,
                "amount": line.amount,
                "invoice_id": line.invoice_id.id,
                "tax_no": line.tax_no,
            }
            if line.claim_id:
                line_vals["claim_id"] = line.claim_id.id
            lines.append(line_vals)
        vals["lines"] = [("create", v) for v in lines]
        pmt_id = self.create(vals, context={"type": vals["type"]})
        return {
            "next": {
                "name": "payment",
                "mode": "form",
                "active_id": pmt_id,
            },
            "flash": "New payment %d copied from %d" % (pmt_id, obj.id),
        }

    def view_journal_entry(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": obj.move_id.id,
            }
        }

    def onchange_type(self, context={}):
        data = context["data"]
        type = data["type"]
        seq_id = data["sequence_id"]
        data["number"] = self._get_number(context={"type": type, "sequence_id": seq_id, "date": data["date"]})
        contact_id = data["contact_id"]
        if contact_id:
            contact = get_model("contact").browse(contact_id)
            if data["type"] == "out":
                data["journal_id"] = contact.pay_out_journal_id.id
            elif data["type"] == "in":
                data["journal_id"] = contact.pay_in_journal_id.id
        self.onchange_journal(context=context)
        return data

    def onchange_date(self, context={}):
        data = context["data"]
        ctx = {
            "type": data["type"],
            "date": data["date"],
            "sequence_id": data["sequence_id"],
        }
        if not data.get("id"):
            number = self._get_number(context=ctx)
            data["number"] = number
        return data

    def onchange_pay_type(self, context={}):
        data = context["data"]
        pay_type = data["pay_type"]
        if pay_type != "invoice":
            return
        contact_id = data["contact_id"]
        type = data["type"]
        cond = [["contact_id", "=", contact_id], ["state", "=", "waiting_payment"]]
        if type == "in":
            #cond.append(["type", "=", "out"])
            inv_type="out"
        elif type == "out":
            #cond.append(["type", "=", "in"])
            inv_type="in"
        lines = []
        if data["type"] == "in":
            rate_type = "sell"
        elif data["type"] == "out":
            rate_type = "buy"
        for inv in get_model("account.invoice").search_browse(cond):
            line_vals={
                "invoice_id": inv.id,
                "invoice_currency_id": inv.currency_id.id,
                "amount_invoice": inv.amount_due,
                "amount": get_model("currency").convert(inv.amount_due, inv.currency_id.id, data["currency_id"], date=data["date"], rate_type=rate_type),
            }
            if inv.type!=inv_type:
                line_vals["amount"]*=-1
            lines.append(line_vals)
        data["invoice_lines"] = lines
        data = self.update_amounts(context)
        return data

    def onchange_employee(self, context={}):
        data = context["data"]
        employee_id = data["employee_id"]
        if data["type"] == "in":
            rate_type = "sell"
        elif data["type"] == "out":
            rate_type = "buy"
        lines = []
        for exp in get_model("expense.claim").search_browse([["employee_id", "=", employee_id]]):
            lines.append({
                "expense_id": exp.id,
                "amount": get_model("currency").convert(exp.amount_total, exp.currency_id.id, data["currency_id"], date=data["date"], rate_type=rate_type),
            })
        data["claim_lines"] = lines
        data = self.update_amounts(context)
        return data

    def get_line_desc(self, context):
        data = context["data"]
        path = context["path"]
        if not data.get("default_line_desc"):
            return
        if not get_data_path(data, path):
            set_data_path(data, path, data.get("memo"))
        return data

    def get_report_data_old(self, context={}):  # XXX: used for receipt/tax invoice report
        obj_id = int(context.get('refer_id'))
        obj = self.browse(obj_id)
        if obj.type == "in":
            rate_type = "sell"
        else:
            rate_type = "buy"
        company = obj.company_id
        settings = get_model('settings').browse(1)
        comp_name = company.name
        comp_fax = settings.fax
        comp_phone = settings.phone
        comp_addr = settings.get_address_str()
        comp_tax_no = settings.tax_no
        reports = []
        for line in obj.invoice_lines:
            inv = line.invoice_id
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
                "tax_invoice_no": line.tax_no or "-",
                "number": obj.number or "-",
                "date": obj.date or "-",
                "ref": inv.number or "-",  # XXX
                "invoice_no": inv.number or "-",
                "currency_code": settings.currency_id.code,
                "amount_subtotal": get_model("currency").convert(inv.amount_subtotal, inv.currency_id.id, settings.currency_id.id, date=obj.date, rate_type=rate_type),
                "amount_tax": get_model("currency").convert(inv.amount_tax, inv.currency_id.id, settings.currency_id.id, date=obj.date, rate_type=rate_type),
                "amount_total": get_model("currency").convert(inv.amount_total, inv.currency_id.id, settings.currency_id.id, date=obj.date, rate_type=rate_type),
                "tax_rate": round(inv.amount_tax * 100 / inv.amount_subtotal or 0, 2),
                "lines": [],
            }
            contact = inv.contact_id
            if settings.logo:
                data['logo'] = get_file_path(settings.logo)
            for inv_line in inv.lines:
                line_vals = {
                    "description": inv_line.description,
                    "amount": get_model("currency").convert(inv_line.amount, inv.currency_id.id, settings.currency_id.id, date=obj.date, rate_type=rate_type),
                    "tax_rate": inv_line.tax_id.rate or 0
                }
                tax = inv_line.tax_id
                if tax:
                    line_vals["tax_rate"] = tax.rate
                data["lines"].append(line_vals)
            reports.append(data)
        return {
            "pages": reports,
            "logo": get_file_path(settings.logo),  # XXX: remove when render_odt fixed
        }

    def gen_wht_no(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="wht_no")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            res = get_model("account.move.line").search([["tax_no", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    def onchange_contact(self, context={}):
        data = context["data"]
        contact_id = data["contact_id"]
        if not contact_id:
            return
        contact = get_model("contact").browse(contact_id)
        if data["type"] == "in":
            data["journal_id"] = contact.pay_in_journal_id.id
        elif data["type"] == "out":
            data["journal_id"] = contact.pay_out_journal_id.id
        if contact.currency_id:
            data["currency_id"] = contact.currency_id.id
            settings = get_model("settings").browse(1)
            if data["currency_id"] == settings.currency_id.id:
                currency_rate = 1.0
            else:
                rate_from = contact.currency_id.get_rate(date=data["date"])
                if not rate_from:
                    raise Exception("Missing currency rate for %s" % contact.currency_id.code)
                rate_to = settings.currency_id.get_rate(date=data["date"])
                if not rate_to:
                    raise Exception("Missing currency rate for %s" % settings.currency_id.code)
                currency_rate = rate_from / (rate_to or 1)
            data["currency_rate"] = currency_rate
        else:
            settings = get_model("settings").browse(1)
            data["currency_id"] = settings.currency_id.id
        self.onchange_journal(context=context)
        return data

    def onchange_journal(self, context={}):
        data = context["data"]
        journal_id = data["journal_id"]
        if journal_id:
            journal = get_model("account.journal").browse(journal_id)
            data["sequence_id"] = journal.sequence_id.id
        else:
            data["sequence_id"] = None
        self.onchange_sequence(context=context)
        return data

    def onchange_payment_account(self, context={}):
        data = context["data"]
        account_id=data["account_id"]
        account=get_model("account.account").browse(account_id)
        if account.sequence_id:
            data["sequence_id"]=account.sequence_id.id
            self.onchange_sequence(context=context)
        return data

    def onchange_sequence(self, context={}):
        data = context["data"]
        num = self._get_number(context={"type": data["type"], "date": data["date"], "sequence_id": data["sequence_id"]})
        data["number"] = num
        return data

    def get_cheque(self, ids, context={}):
        vals={}
        for obj in self.browse(ids):
            c=obj.cheques[0] if obj.cheques else None
            vals[obj.id]={
                "cheque_number": c.number if c else None,
                "cheque_date": c.date if c else None,
                "cheque_bank": c.bank_id.name if c and c.bank_id else None,
                "cheque_branch": c.branch if c and c.bank_id else None,
            }
        return vals

    def onchange_product(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return
        prod = get_model("product").browse(prod_id)
        line["description"] = prod.description or prod.name
        line["qty"] = 1
        if data["type"] == "in":
            if prod.sale_price is not None:
                line["unit_price"] = prod.sale_price
            line["account_id"] = prod.sale_account_id.id
            if not line["account_id"] and prod.categ_id:
                line["account_id"]=prod.categ_id.sale_account_id.id
            line["tax_id"] = prod.sale_tax_id.id
            if not line["tax_id"] and prod.categ_id:
                line["tax_id"]=prod.categ_id.sale_tax_id.id
        elif data["type"] == "out":
            if prod.purchase_price is not None:
                line["unit_price"] = prod.purchase_price
            line["account_id"] = prod.purchase_account_id.id
            if not line["account_id"] and prod.categ_id:
                line["account_id"]=prod.categ_id.purchase_account_id.id
            line["tax_id"] = prod.purchase_tax_id.id
            if not line["tax_id"] and prod.categ_id:
                line["tax_id"]=prod.categ_id.purchase_tax_id.id
        data = self.update_amounts(context)
        return data

    def get_wht_cert_pages(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            company=obj.company_id
            company_name=company.name
            company_address=company.contact_id.default_address_id.address_text if company.contact_id and company.contact_id.default_address_id else "N/A"
            company_tax_no=company.contact_id.tax_no if company.contact_id else "N/A"
            data=[]
            if obj.move_id:
                taxes={}
                for line in obj.move_id.lines:
                    tax_comp=line.tax_comp_id
                    if not tax_comp:
                        continue
                    if tax_comp.type!="wht":
                        continue
                    k=(tax_comp.id,line.contact_id.id or obj.contact_id.id,line.tax_date)
                    taxes.setdefault(k,{"base":0,"tax":0})
                    taxes[k]["base"]+=line.tax_base or 0
                    taxes[k]["tax"]+=abs(line.debit-line.credit)
                for (tax_comp_id,contact_id,tax_date),vals in taxes.items():
                    percent=vals["tax"]*100/vals["base"] if vals["base"] else None
                    contact=get_model("contact").browse(contact_id) if contact_id else None
                    supplier_name=contact.name if contact else "N/A"
                    supplier_address=contact.default_address_id.address_text if contact and contact.default_address_id else "N/A"
                    supplier_tax_no=contact.tax_no if contact else "N/A"
                    data.append({
                        "company_name": company_name,
                        "company_address": company_address,
                        "company_tax_no": company_tax_no,
                        "supplier_name": supplier_name,
                        "supplier_address": supplier_address,
                        "supplier_tax_no": supplier_tax_no,
                        "date": tax_date,
                        "amount_base": vals["base"],
                        "amount_tax": vals["tax"],
                        "tax_percent": percent,
                    })
            vals[obj.id]=data
        return vals

    def get_date_agg(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            d=datetime.strptime(obj.date,"%Y-%m-%d")
            month=d.strftime("%Y-%m")
            week=d.strftime("%Y-W%W")
            vals[obj.id]={
                "date_week": week,
                "date_month": month,
            }
        return vals

Payment.register()
