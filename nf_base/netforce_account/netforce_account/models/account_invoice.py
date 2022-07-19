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
from netforce import utils
from datetime import *
from dateutil.relativedelta import relativedelta
import time
from netforce import config
from netforce import database
from pprint import pprint
from netforce.access import get_active_company, get_active_user, set_active_user, set_active_company
from netforce.utils import get_file_path
from netforce import access
from decimal import *
import json


class Invoice(Model):
    _name = "account.invoice"
    _string = "Invoice"
    _audit_log = True
    _key = ["company_id", "number"]
    _name_field = "number"
    _multi_company = True
    _content_search=True
    _fields = {
        "type": fields.Selection([["out", "Receivable"], ["in", "Payable"]], "Type", required=True),
        "inv_type": fields.Selection([["invoice", "Invoice"], ["credit", "Credit Note"], ["debit", "Debit Note"]], "Subtype", required=True, search=True),
        "number": fields.Char("Number", search=True),
        "sup_inv_number": fields.Char("Supplier Invoice Number", search=True),
        "ref": fields.Char("Ref", size=1024, search=True),
        "memo": fields.Char("Memo", size=1024, search=True),
        "contact_id": fields.Many2One("contact", "Contact", required=True, search=True),
        "contact_categ_id": fields.Many2One("contact.categ", "Contact Category", function="get_contact_categ", function_search="search_contact_categ", search=True),
        "contact_credit": fields.Decimal("Outstanding Credit", function="get_contact_credit"),
        "account_id": fields.Many2One("account.account", "Account"),
        "date": fields.Date("Date", required=True, search=True),
        "due_date": fields.Date("Due Date", search=True),
        "currency_id": fields.Many2One("currency", "Currency", required=True, search=True),
        "tax_type": fields.Selection([["tax_ex", "Tax Exclusive"], ["tax_in", "Tax Inclusive"], ["no_tax", "No Tax"]], "Tax Type", required=True),
        "state": fields.Selection([("draft", "Draft"), ("waiting_approval", "Waiting Approval"), ("waiting_payment", "Waiting Payment"), ("paid", "Paid"), ("voided", "Voided"), ("repeat","Repeating")], "Status", function="get_state", store=True, function_order=20, search=True),
        "lines": fields.One2Many("account.invoice.line", "invoice_id", "Lines"),
        "amount_subtotal": fields.Decimal("Subtotal", function="get_amount", function_multi=True, store=True),
        "amount_tax": fields.Decimal("Tax Amount", function="get_amount", function_multi=True, store=True),
        "amount_total": fields.Decimal("Total", function="get_amount", function_multi=True, store=True),
        "amount_paid": fields.Decimal("Paid Amount", function="get_amount", function_multi=True, store=True),
        "amount_due": fields.Decimal("Due Amount", function="get_amount", function_multi=True, store=True),
        "amount_credit_total": fields.Decimal("Total Credit", function="get_amount", function_multi=True, store=True),
        "amount_credit_remain": fields.Decimal("Remaining Credit", function="get_amount", function_multi=True, store=True),
        "amount_total_cur": fields.Decimal("Total (Conv)", function="get_amount", function_multi=True, store=True),
        "amount_due_cur": fields.Decimal("Due Amount (Conv)", function="get_amount", function_multi=True, store=True),
        "amount_paid_cur": fields.Decimal("Paid Amount (Conv)", function="get_amount", function_multi=True, store=True),
        "amount_credit_remain_cur": fields.Decimal("Remaining Credit (Conv)", function="get_amount", function_multi=True, store=True),
        "amount_rounding": fields.Decimal("Rounding", function="get_amount", function_multi=True, store=True),
        "amount_wht": fields.Decimal("WHT Amount", function="get_amount", function_multi=True, store=True),
        "amount_total_net": fields.Decimal("Net Total Amount", function="get_amount", function_multi=True, store=True),
        "amount_due_net": fields.Decimal("Net Due Amount", function="get_amount", function_multi=True, store=True),
        "wht_percent_text": fields.Char("WHT Percent", function="get_amount", function_multi=True, store=True),
        "qty_total": fields.Decimal("Total Quantity", function="get_qty_total"),
        "attachment": fields.File("Attachment"),
        "payments": fields.One2Many("account.payment.line", "invoice_id", "Payments", condition=[["payment_id.state", "=", "posted"]]), # XXX: deprecated
        "move_id": fields.Many2One("account.move", "Journal Entry"),
        "tax_date_move_id": fields.Many2One("account.move", "Tax Date Adjustment Journal Entry"),
        "reconcile_move_line_id": fields.Many2One("account.move.line", "Reconcile Item"), # XXX: deprecated
        "credit_alloc": fields.One2Many("account.credit.alloc", "credit_id", "Credit Allocation"), # XXX: deprecated
        "credit_notes": fields.One2Many("account.credit.alloc", "invoice_id", "Credit Notes"), # XXX: deprecated
        "currency_rate": fields.Decimal("Currency Rate", scale=6),
        "payment_id": fields.Many2One("account.payment", "Payment"),
        "related_id": fields.Reference([["sale.order", "Sales Order"], ["purchase.order", "Purchase Order"], ["production.order","Production Order"], ["project", "Project"], ["job", "Service Order"], ["service.contract", "Service Contract"]], "Related To"),
        "company_id": fields.Many2One("company", "Company"),
        "amount_discount": fields.Decimal("Discount", function="get_discount",function_multi=True),
        "amount_subtotal_no_discount": fields.Decimal("Subtotal Before Discount", function="get_discount",function_multi=True),
        "bill_address_id": fields.Many2One("address", "Billing Address"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "fixed_assets": fields.One2Many("account.fixed.asset", "invoice_id", "Fixed Assets"),
        "tax_no": fields.Char("Tax Invoice No."),
        "tax_date": fields.Date("Tax Date"),
        "tax_branch_no": fields.Char("Tax Branch No."),
        "pay_method_id": fields.Many2One("payment.method", "Payment Method"),
        "pay_term_id": fields.Many2One("payment.term","Payment Terms"),
        "journal_id": fields.Many2One("account.journal", "Journal"),
        "sequence_id": fields.Many2One("sequence", "Sequence"),
        #"original_invoice_id": fields.Many2One("account.invoice", "Original Invoice"), # XXX: deprecated
        "product_id": fields.Many2One("product","Product",store=False,function_search="search_product",search=True),
        "taxes": fields.One2Many("account.invoice.tax","invoice_id","Taxes"),
        "agg_amount_total": fields.Decimal("Total Amount (Agg)", agg_function=["sum", "amount_total"]),
        "agg_amount_subtotal": fields.Decimal("Total Amount w/o Tax (Agg)", agg_function=["sum", "amount_subtotal"]),
        "year": fields.Char("Year", sql_function=["year", "date"]),
        "quarter": fields.Char("Quarter", sql_function=["quarter", "date"]),
        "month": fields.Char("Month", sql_function=["month", "date"]),
        "week": fields.Char("Week", sql_function=["week", "date"]),
        "transaction_no": fields.Char("Transaction ID",search=True,size=1024),
        "payment_entries": fields.One2Many("account.move.line",None,"Payment Entries",function="get_payment_entries"),
        "journal_date": fields.Date("Journal Date"),
        "user_id": fields.Many2One("base.user", "Owner", search=True),
        "print_form_no": fields.Char("Printed Invoice Form No.",search=True),
        "remarks": fields.Text("Remarks"),
        "product_type": fields.Selection([["product","Product"],["service","Service"]],"Product Type",function="get_product_type"),
        "ship_track_no": fields.Char("Shipping Tracking No.",size=1024),
        "date_week": fields.Char("Week",function="get_date_agg",function_multi=True),
        "date_month": fields.Char("Month",function="get_date_agg",function_multi=True),
        "bill_note_id": fields.Many2One("bill.note","Billing Note"),
        "total_qty": fields.Decimal("Total Qty",function="get_total_qty"),
        "amount_total_words": fields.Text("Amount Total (Words)",function="get_amount_total_words"),
        "ship_term_id": fields.Many2One("ship.term","Shipping Terms"),
        "ship_port_id": fields.Many2One("ship.port","Shipping Port"),
        "amount_total_ship": fields.Decimal("Total Amount (Ship)",function="get_price_ship",function_multi=True), # XXX
        "amount_total_words_ship": fields.Text("Amount Total (Words, Ship)",function="get_price_ship",function_multi=True), # XXX
        "interval_num": fields.Integer("Interval Number"),
        "interval_unit": fields.Selection([["day","Day"],["month","Month"],["year","Year"]],"Interval Unit",search=True),
        "next_date": fields.Date("Next Invoice Date"),
        "next_due_date": fields.Date("Next Due Date"),
        "template_id": fields.Many2One("account.invoice","Invoice Template"),
        "invoices": fields.One2Many("account.invoice","template_id","Invoices"),
        #"cust_orig_invoice_id": fields.Many2One("account.invoice","Original Invoice",function="get_credit_orig_invoice"),
        "orig_invoice_id": fields.Many2One("account.invoice","Original Invoice"),
        "seller_id": fields.Many2One("seller","Seller",search=True),
        "orig_invoice_amount_diff": fields.Decimal("Original Invoice Diff Amount",function="get_orig_invoice_amount_diff"), # XXX: KFF
        "qty_total": fields.Decimal("Total Quantity", function="get_qty_total"),
        "total_net_weight": fields.Decimal("Total Net Weight",function="get_total_weight",function_multi=True),
        "total_gross_weight": fields.Decimal("Total Gross Weight",function="get_total_weight",function_multi=True),
        "brand_id": fields.Many2One("product.brand","Brand"),
        "delivery_term_id": fields.Many2One("delivery.term","Delivery Terms"),
        "packaging_id": fields.Many2One("stock.packaging", "Packaging"),
        "pickings": fields.Many2Many("stock.picking", "Stock Pickings", function="get_pickings"),
        "stock_moves": fields.One2Many("stock.move", "invoice_id", "Stock Movements"),
        "bill_index": fields.Integer("Bill Index",function="get_bill_index"),
        "tax_file_state": fields.Selection([["wait_invoice","Awaiting Tax Invoice"],["wait_file","Awaiting Tax Filing"],["done","Completed"]],"Tax Filing Status",search=True),
        "tax_file_date": fields.Date("Tax Filing Date",search=True),
        "procurement_employee_id": fields.Many2One("hr.employee", "Procurement Person", search=True),
        "time_entries": fields.One2Many("time.entry","invoice_id","Time Entries"),
        "sale_id": fields.Many2One("sale.order","Sales Order",function="get_sale"),
        "picking_id": fields.Many2One("stock.picking","Stock Picking",function="get_picking"),
        "jc_job_id": fields.Many2One("jc.job","Job",function="get_jc_job"),
        "total_bill_hours": fields.Decimal("Total Bill Hours",function="get_time_total",function_multi=True),
        "total_bill_amount": fields.Decimal("Total Bill Amount",function="get_time_total",function_multi=True),
        "time_users": fields.Many2Many("base.user","Time Entry Users",function="get_time_users"),
        "instructions": fields.Text("Instructions",function="get_instructions"),
        "cheque_id": fields.Many2One("account.cheque","Cheque",function="get_cheque"),
        "pay_cash": fields.Boolean("Pay Cash",function="get_pay_flag",function_multi=True),
        "pay_bank": fields.Boolean("Pay Bank",function="get_pay_flag",function_multi=True),
        "pay_cheque": fields.Boolean("Pay Cheque",function="get_pay_flag",function_multi=True),
        "sale_categ_id": fields.Many2One("sale.categ","Sales Category",search=True),
        "approve_user_id": fields.Many2One("base.user", "Approved By", search=True),
        "amount_change": fields.Decimal("Change Amount"),
        "freight_charges": fields.Decimal("Freight Charges"),
        "freight_charges_track_id": fields.Many2One("account.track.categ", "Freight Charges Track-1", condition=[["type", "=", "1"]]),
        "freight_charges_track2_id": fields.Many2One("account.track.categ", "Freight Charges Track-2", condition=[["type", "=", "2"]]),
    }
    #_order = "number desc,date desc,id desc"
    _order = "date desc,number desc,id desc" #Chin: 20201016

    def _get_currency(self, context={}):
        settings = get_model("settings").browse(1)
        return settings.currency_id.id

    def _get_number(self, context={}):
        defaults = context.get("defaults")
        if defaults:  # XXX
            type = defaults.get("type")
            inv_type = defaults.get("inv_type")
        else:
            type = context.get("type")
            inv_type = context.get("inv_type")
        seq_id = context.get("sequence_id")
        if not seq_id:
            seq_type = None
            if type == "out":
                if inv_type in ("invoice", "prepay"):
                    seq_type = "cust_invoice"
                elif inv_type == "credit":
                    seq_type = "cust_credit"
                elif inv_type == "debit":
                    seq_type = "cust_debit"
            elif type == "in":
                if inv_type in ("invoice", "prepay"):
                    seq_type = "supp_invoice"
                elif inv_type == "credit":
                    seq_type = "supp_credit"
                elif inv_type == "debit":
                    seq_type = "supp_debit"
            if not seq_type:
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

    _defaults = {
        "state": "draft",
        "currency_id": _get_currency,
        "tax_type": "tax_ex",
        "number": _get_number,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "company_id": lambda *a: get_active_company(),
        "user_id": lambda *a: get_active_user(),
    }
    _constraints = ["check_fields"]

    def search_product(self, clause, context={}):
        product_id = clause[2]
        product = get_model("product").browse(product_id)
        product_ids = [product_id]
        for var in product.variants:
            product_ids.append(var.id)
        for comp in product.components:
            product_ids.append(comp.component_id.id)
        invoice_ids = []
        for line in get_model("account.invoice.line").search_browse([["product_id","in",product_ids]]):
            invoice_ids.append(line.invoice_id.id)
        cond = [["id","in",invoice_ids]]
        return cond

    def check_fields(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.state in ("waiting_approval", "waiting_payment"):
                if obj.inv_type == "invoice":
                    if not obj.due_date:
                        raise Exception("Missing due date")
                    if obj.due_date<obj.date:
                        raise Exception("Due date is before invoice date")
                # if not obj.lines: # XXX: in myob, lines can be empty...
                #    raise Exception("Lines are empty")

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            name = obj.number
            if not name:
                if obj.inv_type == "invoice":
                    name = "Invoice"
                elif obj.inv_type == "credit":
                    name = "Credit Note"
                elif obj.inv_type == "prepay":
                    name = "Prepayment"
                elif obj.inv_type == "overpay":
                    name = "Overpayment"
            #if obj.ref:
            #    name += " [%s]" % obj.ref
            vals.append((obj.id, name))
        return vals

    def create(self, vals, context={}):
        id = super(Invoice, self).create(vals, context=context)
        self.function_store([id])
        self.trigger([id],"create")
        return id

    def write(self, ids, vals, **kw):
        super(Invoice, self).write(ids, vals, **kw)
        self.function_store(ids)
        sale_ids = []
        purch_ids = []
        for inv in self.browse(ids):
            for line in inv.lines:
                if line.sale_id:
                    sale_ids.append(line.sale_id.id)
                if line.purch_id:
                    purch_ids.append(line.purch_id.id)
        if sale_ids:
            get_model("sale.order").function_store(sale_ids)
        if purch_ids:
            get_model("purchase.order").function_store(purch_ids)

    def delete(self, ids, context={}):
        sale_ids = []
        purch_ids = []
        for inv in self.browse(ids):
            if inv.inv_type not in ("prepay", "overpay"):
                if inv.state not in ("draft", "waiting_approval", "voided", "repeat"):
                    raise Exception("Can't delete invoice with this status")
            for line in inv.lines:
                if line.sale_id:
                    sale_ids.append(line.sale_id.id)
                if line.purch_id:
                    purch_ids.append(line.purch_id.id)
        super(Invoice, self).delete(ids, context=context)
        if sale_ids:
            get_model("sale.order").function_store(sale_ids)
        if purch_ids:
            get_model("purchase.order").function_store(purch_ids)

    def function_store(self, ids, field_names=None, context={}):
        super().function_store(ids, field_names, context)
        sale_ids = []
        purch_ids = []
        for obj in self.browse(ids):
            for line in obj.lines:
                if line.sale_id:
                    sale_ids.append(line.sale_id.id)
                if line.purch_id:
                    purch_ids.append(line.purch_id.id)
        if sale_ids:
            get_model("sale.order").function_store(sale_ids)
        if purch_ids:
            get_model("purchase.order").function_store(purch_ids)

    def submit_for_approval(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.state != "draft":
                raise Exception("Invalid state")
            obj.write({"state": "waiting_approval"})
        self.trigger(ids, "submit_for_approval")
        return {
            "flash": "Invoice submitted for approval."
        }

    def approve(self, ids, context={}):
        if not ids:
            return
        obj = self.browse(ids)[0]
        if obj.state not in ("draft", "waiting_approval"):
            raise Exception("Invalid state")
        access.set_active_company(obj.company_id.id)
        obj.post()
        user_id=access.get_active_user()
        obj.write({"approve_user_id": user_id})
        if obj.inv_type == "invoice":
            msg = "Invoice approved."
            if obj.type == "in":
                obj.create_fixed_assets()
        elif obj.inv_type == "credit":
            msg = "Credit note approved."
        elif obj.inv_type == "debit":
            msg = "Debit note approved."
        return {
            "flash": msg,
        }

    def approve_async(self, ids, context={}):
        user_id=access.get_active_user()
        company_id=access.get_active_company()
        vals={
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "account.invoice",
            "method": "approve",
            "user_id": user_id,
            "company_id": company_id,
            "args": json.dumps({
                "ids": ids,
            }),
        }
        get_model("bg.task").create(vals)

    def calc_taxes(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.taxes.delete()
        settings = get_model("settings").browse(1)
        if obj.currency_rate:
            currency_rate = obj.currency_rate
        else:
            if obj.currency_id.id == settings.currency_id.id:
                currency_rate = 1
            else:
                rate_from = obj.currency_id.get_rate(date=obj.date)
                if not rate_from:
                    raise Exception("Missing currency rate for %s" % obj.currency_id.code)
                rate_to = settings.currency_id.get_rate(date=obj.date)
                if not rate_to:
                    raise Exception("Missing currency rate for %s" % settings.currency_id.code)
                currency_rate = rate_from / rate_to
            obj.write({"currency_rate": currency_rate})
        taxes = {}
        tax_nos = []
        total_amt = 0
        total_base = 0
        total_tax = 0
        for line in obj.lines:
            #cur_amt = get_model("currency").convert(
            #    line.amount, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
            cur_amt = line.amount # XXX
            tax_id = line.tax_id
            if tax_id and obj.tax_type != "no_tax":
                base_amt = get_model("account.tax.rate").compute_base(tax_id, cur_amt, tax_type=obj.tax_type)
                if settings.rounding_account_id:
                    base_amt=get_model("currency").round(obj.currency_id.id,base_amt)
                tax_comps = get_model("account.tax.rate").compute_taxes(tax_id, base_amt, when="invoice")
                for comp_id, tax_amt in tax_comps.items():
                    tax_vals = taxes.setdefault(comp_id, {"tax_amt": 0, "base_amt": 0})
                    tax_vals["tax_amt"] += tax_amt
                    tax_vals["base_amt"] += base_amt
            else:
                base_amt = cur_amt
        for comp_id, tax_vals in taxes.items():
            comp = get_model("account.tax.component").browse(comp_id)
            acc_id = comp.account_id.id
            if not acc_id:
                raise Exception("Missing account for tax component %s" % comp.name)
            vals = {
                "invoice_id": obj.id,
                "tax_comp_id": comp_id,
                "base_amount": get_model("currency").round(obj.currency_id.id,tax_vals["base_amt"]),
                "tax_amount": get_model("currency").round(obj.currency_id.id,tax_vals["tax_amt"]),
            }
            if comp.type in ("vat", "vat_exempt"):
                if obj.type == "out":
                    if obj.tax_no:
                        tax_no = obj.tax_no
                    else:
                        tax_no = self.gen_tax_no(exclude=tax_nos, context={"date": obj.date})
                        tax_nos.append(tax_no)
                        obj.write({"tax_no": tax_no})
                    vals["tax_no"] = tax_no
                elif obj.type == "in":
                    vals["tax_no"] = obj.tax_no
            get_model("account.invoice.tax").create(vals)

    def set_pay_term(self, ids, context={}):
        obj=self.browse(ids[0])
        pay_term=obj.pay_term_id
        if not pay_term:
            return
        if pay_term.days:
            d=datetime.strptime(obj.date,"%Y-%m-%d")
            d+=timedelta(days=pay_term.days)
            due_date=d.strftime("%Y-%m-%d")
            obj.write({"due_date":due_date})

    def post(self, ids, context={}):
        t0 = time.time()
        settings = get_model("settings").browse(1)
        for obj in self.browse(ids):
            if obj.related_id:
                for line in obj.lines:
                    if not line.related_id:
                        line.write({"related_id":"%s,%d"%(obj.related_id._model,obj.related_id.id)})
            if obj.pay_term_id:
                obj.set_pay_term()
            obj.check_related()
            #if obj.amount_total == 0:
            #    raise Exception("Invoice total is zero") # need in some cases
            if obj.amount_total < 0:
                raise Exception("Invoice total is negative")
            if not obj.taxes:
                obj.calc_taxes()
                obj=obj.browse()[0]
            contact = obj.contact_id
            if obj.account_id:
                account_id=obj.account_id.id
            elif obj.orig_invoice_id and obj.orig_invoice_id.account_id:
                account_id=obj.orig_invoice_id.account_id.id
            else:
                if obj.type == "out":
                    account_id = contact.account_receivable_id.id or (contact.categ_id and contact.categ_id.account_receivable_id.id) or obj.currency_id.account_receivable_id.id or settings.account_receivable_id.id
                    if not account_id:
                        raise Exception("Account receivable not found")
                elif obj.type == "in":
                    account_id = contact.account_payable_id.id or (contact.categ_id and contact.categ_id.account_payable_id.id) or obj.currency_id.account_payable_id.id or settings.account_payable_id.id
                    if not account_id:
                        raise Exception("Account payable not found")
            account=get_model("account.account").browse(account_id)
            if account.currency_id.id!=obj.currency_id.id:
                raise Exception("Currency of accounts %s is different than invoice (%s / %s)"%(account.code,account.currency_id.code,obj.currency_id.code))
            sign = obj.type == "out" and 1 or -1
            if obj.inv_type == "credit":
                sign *= -1
            obj.write({"account_id": account_id})
            if obj.type == "out":
                desc = "Sale; " + contact.name
            elif obj.type == "in":
                desc = "Purchase; " + contact.name
            if obj.memo:
                desc=obj.memo
            if obj.type == "out":
                journal_id = obj.journal_id.id or settings.sale_journal_id.id
                if not journal_id:
                    raise Exception("Sales journal not found")
            elif obj.type == "in":
                journal_id = obj.journal_id.id or settings.purchase_journal_id.id
                if not journal_id:
                    raise Exception("Purchases journal not found")
            if obj.currency_rate:
                currency_rate = obj.currency_rate
            else:
                if obj.currency_id.id == settings.currency_id.id:
                    currency_rate = 1
                else:
                    rate_from = obj.currency_id.get_rate(date=obj.date)
                    if not rate_from:
                        raise Exception("Missing currency rate for %s" % obj.currency_id.code)
                    rate_to = settings.currency_id.get_rate(date=obj.date)
                    if not rate_to:
                        raise Exception("Missing currency rate for %s" % settings.currency_id.code)
                    currency_rate = rate_from / rate_to
                obj.write({"currency_rate": currency_rate})
            move_vals = {
                "journal_id": journal_id,
                "number": obj.number,
                "date": obj.journal_date or obj.date,
                "ref": obj.ref,
                "narration": desc,
                "related_id": "account.invoice,%s" % obj.id,
                "company_id": obj.company_id.id,
            }
            lines = []
            t01 = time.time()
            for line in obj.lines:
                cur_amt = get_model("currency").convert(
                    line.amount, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
                tax_id = line.tax_id
                if tax_id and obj.tax_type != "no_tax":
                    base_amt = get_model("account.tax.rate").compute_base(tax_id, cur_amt, tax_type=obj.tax_type)
                else:
                    base_amt = cur_amt
                acc_id = line.account_id.id
                if not acc_id:
                    raise Exception("Missing account for invoice line '%s'" % line.description)
                amt = base_amt * sign
                if line.track_distrib_id:
                    for dist_line in line.track_distrib_id.lines: 
                        dist_amt=amt*(dist_line.percent or 0)/100
                        line_vals = {
                            #"description": line.description,
                            "description": desc,
                            "account_id": acc_id,
                            "credit": dist_amt > 0 and dist_amt or 0,
                            "debit": dist_amt < 0 and -dist_amt or 0,
                            "track_id": dist_line.track_id.id,
                            "track2_id": line.track2_id.id,
                            "contact_id": contact.id,
                            "product_id": line.product_id.id,
                        }
                        lines.append(line_vals)
                else:
                    line_vals = {
                        #"description": line.description,
                        "description": desc,
                        "account_id": acc_id,
                        "credit": amt > 0 and amt or 0,
                        "debit": amt < 0 and -amt or 0,
                        "track_id": line.track_id.id,
                        "track2_id": line.track2_id.id,
                        "contact_id": contact.id,
                        "product_id": line.product_id.id,
                    }
                    lines.append(line_vals)
            for tax in obj.taxes:
                comp = tax.tax_comp_id
                acc_id = comp.account_id.id
                if not tax.tax_date and comp.account_pending_id:
                    acc_id=comp.account_pending_id.id
                if not acc_id:
                    raise Exception("Missing account for tax component %s" % comp.name)
                cur_tax_amt = get_model("currency").convert(
                    tax.tax_amount, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
                cur_base_amt = get_model("currency").convert(
                    tax.base_amount, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
                amt = sign * cur_tax_amt
                line_vals = {
                    "description": desc,
                    "account_id": acc_id,
                    "credit": amt > 0 and amt or 0,
                    "debit": amt < 0 and -amt or 0,
                    "tax_comp_id": comp.id,
                    "tax_base": cur_base_amt,
                    "contact_id": contact.id,
                    "invoice_id": obj.id,
                    "tax_no": tax.tax_no,
                    "tax_date": obj.date,
                }
                lines.append(line_vals)
            
            #Chin
            if obj.freight_charges:
                if obj.type == 'out':
                    freight_charge_account_id = settings.freight_charge_cust_id.id
                else:
                    freight_charge_account_id = settings.freight_charge_supp_id.id
                if not freight_charge_account_id:
                    raise Exception("Freight Charge Account not defined. Check Finanacial Settings")
                amt = obj.freight_charges * sign
                line_vals = {
                    #"description": line.description,
                    "description": desc,
                    "account_id": freight_charge_account_id,
                    "credit": amt > 0 and amt or 0,
                    "debit": amt < 0 and -amt or 0,
                    "contact_id": contact.id,
                }
                lines.append(line_vals)
            #End Edit                

            t02 = time.time()
            dt01 = (t02 - t01) * 1000
            print("post dt01", dt01)
            groups = {}
            keys = ["description", "account_id", "track_id", "track2_id", "track_distrib_id", "tax_comp_id", "contact_id", "invoice_id", "reconcile_id"]
            for line in lines:
                key_val = tuple(line.get(k) for k in keys)
                if key_val in groups:
                    group = groups[key_val]
                    group["debit"] += line["debit"]
                    group["credit"] += line["credit"]
                    if line.get("tax_base"):
                        if "tax_base" not in group:
                            group["tax_base"] = 0
                        group["tax_base"] += line["tax_base"]
                else:
                    groups[key_val] = line.copy()
            group_lines = sorted(groups.values(), key=lambda l: (l["debit"], l["credit"]))
            for line in group_lines:
                amt = line["debit"] - line["credit"]
                amt = get_model("currency").round(obj.currency_id.id,amt)
                if amt >= 0:
                    line["debit"] = amt
                    line["credit"] = 0
                else:
                    line["debit"] = 0
                    line["credit"] = -amt
            amt = 0
            for line in group_lines:
                amt -= line["debit"] - line["credit"]
            line_vals = {
                "description": desc,
                "account_id": account_id,
                "debit": amt > 0 and amt or 0,
                "credit": amt < 0 and -amt or 0,
                "due_date": obj.due_date,
                "contact_id": contact.id,
            }
            acc = get_model("account.account").browse(account_id)
            if acc.currency_id.id != settings.currency_id.id:
                if acc.currency_id.id != obj.currency_id.id:
                    raise Exception("Invalid account currency for this invoice: %s" % acc.code)
                line_vals["amount_cur"] = obj.amount_total
            move_vals["lines"] = [("create", line_vals)]
            move_vals["lines"] += [("create", vals) for vals in group_lines]
            t03 = time.time()
            dt02 = (t03 - t02) * 1000
            print("post dt02", dt02)
            move_id = get_model("account.move").create(move_vals)
            t04 = time.time()
            dt03 = (t04 - t03) * 1000
            print("post dt03", dt03)
            get_model("account.move").post([move_id])
            t05 = time.time()
            dt04 = (t05 - t04) * 1000
            print("post dt04", dt04)
            obj.write({"move_id": move_id, "state": "waiting_payment"})
            t06 = time.time()
            dt05 = (t06 - t05) * 1000
            print("post dt05", dt05)
        t1 = time.time()
        dt = (t1 - t0) * 1000
        print("invoice.post <<< %d ms" % dt)

    def post_tax_date(self, ids, context={}):
        obj=self.browse(ids[0])
        settings = get_model("settings").browse(1)
        if not obj.tax_date:
            raise Exception("Missing tax date")
        if obj.type == "out":
            journal_id = obj.journal_id.id or settings.sale_journal_id.id
            if not journal_id:
                raise Exception("Sales journal not found")
        elif obj.type == "in":
            journal_id = obj.journal_id.id or settings.purchase_journal_id.id
            if not journal_id:
                raise Exception("Purchases journal not found")
        sign = obj.type == "out" and 1 or -1
        if obj.inv_type == "credit":
            sign *= -1
        currency_rate = obj.currency_rate or 1
        desc="Tax date adjustment"
        move_vals = {
            "journal_id": journal_id,
            "number": obj.number+"-TAX-ADJUST",
            "date": obj.tax_date,
            "ref": obj.ref,
            "narration": "Tax",
            "related_id": "account.invoice,%s" % obj.id,
            "company_id": obj.company_id.id,
        }
        lines = []
        for tax in obj.taxes:
            comp = tax.tax_comp_id
            acc_id = comp.account_id.id
            if not acc_id:
                raise Exception("Missing account for tax component %s" % comp.name)
            acc_pending_id = comp.account_pending_id.id
            if not acc_pending_id:
                raise Exception("Missing pending account for tax component %s" % comp.name)
            cur_tax_amt = get_model("currency").convert(
                tax.tax_amount, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
            cur_base_amt = get_model("currency").convert(
                tax.base_amount, obj.currency_id.id, settings.currency_id.id, rate=currency_rate)
            amt = sign * cur_tax_amt
            amt_pending = -amt
            line_vals = {
                "description": desc,
                "account_id": acc_pending_id,
                "credit": amt_pending > 0 and amt_pending or 0,
                "debit": amt_pending < 0 and -amt_pending or 0,
                "tax_comp_id": comp.id,
                "tax_base": cur_base_amt,
                "contact_id": obj.contact_id.id,
                "invoice_id": obj.id,
                "tax_no": tax.tax_no,
                "tax_date": obj.tax_date,
            }
            lines.append(line_vals)
            line_vals = {
                "description": desc,
                "account_id": acc_id,
                "credit": amt > 0 and amt or 0,
                "debit": amt < 0 and -amt or 0,
                "tax_comp_id": comp.id,
                "tax_base": cur_base_amt,
                "contact_id": obj.contact_id.id,
                "invoice_id": obj.id,
                "tax_no": tax.tax_no,
                "tax_date": obj.tax_date,
            }
            lines.append(line_vals)
            tax.write({"tax_date": obj.tax_date})
        move_vals["lines"] = [("create", l) for l in lines]
        move_id = get_model("account.move").create(move_vals)
        get_model("account.move").post([move_id])
        obj.write({"tax_date_move_id": move_id})

    def repost_invoices(self, context={}):  # XXX
        ids = self.search([["state", "in", ("waiting_payment", "paid")]], order="date")
        for obj in self.browse(ids):
            print("invoice %d..." % obj.id)
            if not obj.move_id:
                raise Exception("No journal entry for invoice #%d" % obj.id)
            obj.move_id.delete()
            obj.post()

    def void(self, ids, context={}):
        print("invoice.void", ids)
        obj = self.browse(ids)[0]
        if obj.state not in ("draft", "waiting_payment","paid"):
            raise Exception("Invalid invoice state")
        if obj.payment_entries:
            raise Exception("Can't void invoice because there are still related payment entries")
        if obj.move_id:
            obj.move_id.void()
            obj.move_id.delete()
        obj.write({"state": "voided"})

    def to_draft(self, ids, context={}):
        for obj in self.browse(ids):
            #if obj.state not in ("waiting_payment","voided","paid"):
            #    raise Exception("Invalid status")
            if obj.payment_entries:
                raise Exception("There are still payment entries for this invoice")
            if obj.move_id:
                obj.move_id.void()
                obj.move_id.delete()
            if obj.reconcile_move_line_id: # XXX: deprecated
                obj.write({"reconcile_move_line_id":None})
            obj.taxes.delete()
            obj.write({"state": "draft", "account_id": None})

    def get_amount(self, ids, context={}):
        t0 = time.time()
        settings = get_model("settings").browse(1)
        res = {}
        for inv in self.browse(ids):
            vals = {}
            subtotal = 0
            tax = 0
            for line in inv.lines:
                tax_id = line.tax_id
                if tax_id and inv.tax_type != "no_tax":
                    base_amt = get_model("account.tax.rate").compute_base(tax_id, line.amount, tax_type=inv.tax_type)
                    tax_comps = get_model("account.tax.rate").compute_taxes(tax_id, base_amt, when="invoice")
                    for comp_id, tax_amt in tax_comps.items():
                        tax += tax_amt
                else:
                    base_amt = line.amount
                subtotal += base_amt
            subtotal=get_model("currency").round(inv.currency_id.id,subtotal)
            tax=get_model("currency").round(inv.currency_id.id,tax)
            freight_charges=get_model("currency").round(inv.currency_id.id,inv.freight_charges) if inv.freight_charges else 0 #Chin
            vals["amount_subtotal"] = subtotal
            if inv.taxes:
                tax=sum(t.tax_amount for t in inv.taxes)
            vals["amount_tax"] = tax
            if inv.tax_type == "tax_in":
                vals["amount_rounding"] = sum(l.amount for l in inv.lines) - (subtotal + tax)
            else:
                vals["amount_rounding"] = 0
            vals["amount_total"] = subtotal + tax + freight_charges + vals["amount_rounding"] #Chin
            vals["amount_total_cur"] = get_model("currency").convert(
                vals["amount_total"], inv.currency_id.id, settings.currency_id.id, round=True, rate=inv.currency_rate)
            vals["amount_credit_total"] = vals["amount_total"]
            paid_amt = 0
            for pmt in inv.payment_entries:
                if pmt.amount_cur is not None:
                    pmt_amt=abs(pmt.amount_cur) # XXX: no need for abs, amount_cur always>=0
                else:
                    if inv.type == "in":
                        pmt_amt=pmt.debit
                    else:
                        pmt_amt=pmt.credit
                paid_amt+=pmt_amt
            vals["amount_paid"] = paid_amt
            if inv.inv_type in ("invoice", "debit"):
                vals["amount_due"] = vals["amount_total"] - paid_amt
            elif inv.inv_type in ("credit", "prepay", "overpay"):
                cred_amt = 0
                for pmt in inv.payment_entries:
                    if pmt.amount_cur is not None:
                        pmt_amt=abs(pmt.amount_cur)
                    else:
                        if inv.type == "in":
                            pmt_amt=pmt.credit
                        else:
                            pmt_amt=pmt.debit
                    cred_amt += pmt_amt
                vals["amount_credit_remain"] = vals["amount_total"] - cred_amt
                vals["amount_due"] = -vals["amount_credit_remain"]
            else:
                vals["amount_due"]=0
            vals["amount_due_cur"] = get_model("currency").convert(
                vals["amount_due"], inv.currency_id.id, settings.currency_id.id, round=True, rate=inv.currency_rate)
            vals["amount_paid_cur"] = get_model("currency").convert(
                vals["amount_paid"], inv.currency_id.id, settings.currency_id.id, round=True, rate=inv.currency_rate)
            vals["amount_credit_remain_cur"] = get_model("currency").convert(
                vals.get("amount_credit_remain", 0), inv.currency_id.id, settings.currency_id.id, round=True, rate=inv.currency_rate)
            wht=0
            for line in inv.lines:
                tax_id = line.tax_id
                if tax_id and inv.tax_type != "no_tax":
                    base_amt = get_model("account.tax.rate").compute_base(tax_id, line.amount, tax_type=inv.tax_type)
                    tax_comps = get_model("account.tax.rate").compute_taxes(tax_id, base_amt, when="direct_payment")
                    for comp_id, tax_amt in tax_comps.items():
                        comp = get_model("account.tax.component").browse(comp_id)
                        if comp.type == "wht":
                            wht -= tax_amt
            vals["amount_wht"]=wht
            vals["amount_total_net"]=vals["amount_total"]-wht
            vals["amount_due_net"]=vals["amount_due"]-wht
            wht_pct=wht*100/subtotal if subtotal else None
            vals["wht_percent_text"]=str(int(wht_pct))+"%" if wht_pct else "N/A"
            res[inv.id] = vals
        t1 = time.time()
        dt = (t1 - t0) * 1000
        print("invoice.get_amount <<< %d ms" % dt)
        return res

    def get_qty_total(self, ids, context={}):
        res = {}
        for obj in self.browse(ids):
            qty = sum([line.qty or 0 for line in obj.lines])
            res[obj.id] = qty
        return res

    def update_amounts(self, context):
        data = context["data"]
        settings=get_model("settings").browse(1)
        currency_id = data["currency_id"]
        data["amount_subtotal"] = 0
        data["amount_tax"] = 0
        tax_type = data["tax_type"]
        tax_in_total = 0
        for line in data["lines"]:
            if not line:
                continue
            if line.get("unit_price") is not None:
                amt = (line.get("qty") or 0) * (line.get("unit_price") or 0)
                if line.get("discount"):
                    disc = amt * line["discount"] / 100
                    amt -= disc
                if line.get("discount_amount"):
                    amt -= line["discount_amount"]
                line["amount"] = amt
            else:
                amt = line.get("amount") or 0
            tax_id = line.get("tax_id")
            if tax_id and tax_type != "no_tax":
                base_amt = get_model("account.tax.rate").compute_base(tax_id, amt, tax_type=tax_type)
                tax_comps = get_model("account.tax.rate").compute_taxes(tax_id, base_amt, when="invoice")
                for comp_id, tax_amt in tax_comps.items():
                    data["amount_tax"] += tax_amt
            else:
                base_amt = amt
            data["amount_subtotal"] += Decimal(base_amt)
        if tax_type == "tax_in":
            data["amount_rounding"] = sum(
                l.get("amount") or 0 for l in data["lines"] if l) - (data["amount_subtotal"] + data["amount_tax"])
        else:
            data["amount_rounding"] = 0
        data["amount_total"] = data["amount_subtotal"] + data["amount_tax"] + data["amount_rounding"]
        return data

    def onchange_amount(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        amount=line.get("amount")
        qty=line.get("qty")
        if amount is not None and qty:
            line["unit_price"]=amount/qty
        data = self.update_amounts(context)
        return data

    def onchange_product(self, context):
        data = context["data"]
        type = data["type"]
        path = context["path"]
        contact_id = data.get("contact_id")
        contact = get_model("contact").browse(contact_id) if contact_id else None
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        if not prod_id:
            return
        prod = get_model("product").browse(prod_id)
        line["description"] = prod.description or prod.name
        line["qty"] = 1
        if prod.uom_id is not None:
            line["uom_id"] = prod.uom_id.id
        if type == "out":
            if prod.sale_price is not None:
                line["unit_price"] = prod.sale_price
            if prod.sale_account_id is not None:
                line["account_id"] = prod.sale_account_id.id
                if not line["account_id"] and prod.categ_id:
                    line["account_id"]=prod.categ_id.sale_account_id.id
            if prod.sale_tax_id is not None:
                line["tax_id"] = (contact and contact.sale_tax_id.id) or prod.sale_tax_id.id
                if not line["tax_id"] and prod.categ_id:
                    line["tax_id"]=prod.categ_id.sale_tax_id.id
        elif type == "in":
            if prod.purchase_price is not None:
                line["unit_price"] = prod.purchase_price
            if prod.purchase_account_id is not None:
                line["account_id"] = prod.purchase_account_id.id
                if not line["account_id"] and prod.categ_id:
                    line["account_id"]=prod.categ_id.purchase_account_id.id
            if prod.purchase_tax_id is not None:
                line["tax_id"] = (contact and contact.purchase_tax_id.id) or prod.purchase_tax_id.id
                if not line["tax_id"] and prod.categ_id:
                    line["tax_id"]=prod.categ_id.purchase_tax_id.id
        data = self.update_amounts(context)
        return data

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
        return data

    def onchange_contact(self, context):
        data = context["data"]
        contact_id = data.get("contact_id")
        if not contact_id:
            return {}
        contact = get_model("contact").browse(contact_id)
        data["bill_address_id"] = contact.get_address(pref_type="billing")
        if data["type"] == "out":
            data["journal_id"] = contact.sale_journal_id.id
        elif data["type"] == "in":
            data["journal_id"] = contact.purchase_journal_id.id
        self.onchange_journal(context=context)
        if contact.currency_id:
            data["currency_id"] = contact.currency_id.id
        else:
            settings = get_model("settings").browse(1)
            data["currency_id"] = settings.currency_id.id
        pay_term_id=None
        if data["type"]=="out":
            pay_term_id=contact.sale_pay_term_id.id
        elif data["type"]=="in":
            pay_term_id=contact.purchase_pay_term_id.id
        if pay_term_id:
            data["pay_term_id"]=pay_term_id
            data=self.onchange_pay_term(context)
        return data

    def view_invoice(self, ids, context={}):
        obj = self.browse(ids[0])
        if obj.type == "out":
            action = "cust_invoice"
            if obj.state == "repeat":
                layout = "cust_repeat_form"
            elif obj.inv_type == "invoice":
                layout = "cust_invoice_form"
            elif obj.inv_type == "credit":
                layout = "cust_credit_form"
            elif obj.inv_type == "debit":
                layout = "cust_debit_form"
            elif obj.inv_type == "prepay":
                layout = "cust_prepay_form"
            elif obj.inv_type == "overpay":
                layout = "cust_overpay_form"
        elif obj.type == "in":
            action = "supp_invoice"
            if obj.state == "repeat":
                layout = "supp_repeat_form"
            elif obj.inv_type == "invoice":
                layout = "supp_invoice_form"
            elif obj.inv_type == "credit":
                layout = "supp_credit_form"
            elif obj.inv_type == "debit":
                layout = "supp_debit_form"
            elif obj.inv_type == "prepay":
                layout = "supp_prepay_form"
            elif obj.inv_type == "overpay":
                layout = "supp_overpay_form"
        else:
            raise Exception("Invalid invoice type (%s)"%obj.id)
        next_action={
            "name": action,
            "mode": "form",
            "form_layout": layout,
            "active_id": obj.id,
        }
        if context.get("search_condition"):
            next_action["search_condition"]=context["search_condition"]
        call_action=context.get("action",{})
        if call_action.get("tab_no"):
            next_action["tab_no"]=call_action["tab_no"]
        if call_action.get("offset"):
            next_action["offset"]=call_action["offset"]
        if call_action.get("search_condition"):
            next_action["search_condition"]=call_action["search_condition"]
        return {
            "next": next_action,
        }

    def get_contact_credit(self, ids, context={}):
        obj = self.browse(ids[0])
        contact = get_model("contact").browse(obj.contact_id.id, context={"currency_id": obj.currency_id.id})
        vals = {}
        if obj.type == "out":
            amt = contact.receivable_credit
        elif obj.type == "in":
            amt = contact.payable_credit
        vals[obj.id] = amt
        return vals

    def get_state(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            state = obj.state
            if state == "waiting_payment":
                if obj.inv_type in ("invoice", "debit"):
                    if obj.amount_due == 0:
                        state = "paid"
                elif obj.inv_type in ("credit", "prepay", "overpay"):
                    if obj.amount_credit_remain == 0:
                        state = "paid"
            elif state == "paid":
                if obj.inv_type in ("invoice", "debit"):
                    if obj.amount_due > 0:
                        state = "waiting_payment"
                elif obj.inv_type in ("credit", "prepay", "overpay"):
                    if obj.amount_credit_remain > 0:
                        state = "waiting_payment"
            vals[obj.id] = state
        return vals

    def copy(self, ids, context):
        obj = self.browse(ids)[0]
        lines=[]
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
                "account_id": line.account_id.id,
                "sale_id": line.sale_id.id,
                "purch_id": line.purch_id.id,
                "amount": line.amount,
                "track_id": line.track_id.id, # Chin: Added 2020-10-10
            }
            lines.append(("create", line_vals))
        vals={
            "number": obj.number+" (copy)",
            "lines": lines,
            "state": "draft",
            "move_id": None,
        }
        new_id = obj._copy(vals)[0]
        new_obj = self.browse(new_id)
        return {
            "next": {
                "name": "view_invoice",
                "active_id": new_id,
            },
            "flash": "Invoice %s copied to %s" % (obj.number, new_obj.number),
        }

    def copy_to_credit_note(self, ids, context):
        obj = self.browse(ids)[0]
        vals = {
            "type": obj.type,
            "inv_type": "credit",
            "ref": obj.number,
            "contact_id": obj.contact_id.id,
            "bill_address_id": obj.bill_address_id.id,
            "currency_id": obj.currency_id.id,
            "currency_rate": obj.currency_rate,
            "tax_type": obj.tax_type,
            "memo": obj.memo,
            "tax_no": obj.tax_no,
            "pay_method_id": obj.pay_method_id.id,
            "orig_invoice_id": obj.id,
            "lines": [],
        }
        if obj.related_id:
            vals["related_id"] = "%s,%s" % (obj.related_id._model, obj.related_id.id)
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
                "account_id": line.account_id.id,
                "sale_id": line.sale_id.id,
                "purch_id": line.purch_id.id,
                "amount": line.amount,
            }
            vals["lines"].append(("create", line_vals))
        new_id = self.create(vals, context={"type": vals["type"], "inv_type": vals["inv_type"]})
        new_obj = self.browse(new_id)
        msg = "Credit note %s created from invoice %s" % (new_obj.number, obj.number)
        return {
            "next": {
                "name": "view_invoice",
                "active_id": new_id,
            },
            "flash": msg,
            "invoice_id": new_id,
        }

    def copy_to_debit_note(self, ids, context):
        obj = self.browse(ids)[0]
        vals = {
            "type": obj.type,
            "inv_type": "debit",
            "ref": obj.number,
            "contact_id": obj.contact_id.id,
            "bill_address_id": obj.bill_address_id.id,
            "currency_id": obj.currency_id.id,
            "currency_rate": obj.currency_rate,
            "tax_type": obj.tax_type,
            "memo": obj.memo,
            "tax_no": obj.tax_no,
            "pay_method_id": obj.pay_method_id.id,
            "orig_invoice_id": obj.id,
            "lines": [],
        }
        if obj.related_id:
            vals["related_id"] = "%s,%s" % (obj.related_id._model, obj.related_id.id)
        for line in obj.lines:
            line_vals = {
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": 0,
                "tax_id": line.tax_id.id,
                "account_id": line.account_id.id,
                "sale_id": line.sale_id.id,
                "purch_id": line.purch_id.id,
                "amount": 0,
            }
            vals["lines"].append(("create", line_vals))
        new_id = self.create(vals, context={"type": vals["type"], "inv_type": vals["inv_type"]})
        new_obj = self.browse(new_id)
        msg = "Debit note %s created from invoice %s" % (new_obj.number, obj.number)
        return {
            "next": {
                "name": "view_invoice",
                "active_id": new_id,
            },
            "flash": msg,
            "invoice_id": new_id,
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

    def view_tax_date_journal_entry(self, ids, context={}):
        obj = self.browse(ids)[0]
        if not obj.tax_date_move_id:
            raise Exception("Missing journal entry")
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": obj.tax_date_move_id.id,
            }
        }

    def gen_tax_no(self, exclude=None, context={}):
        company_id = get_active_company()  # XXX: improve this?
        seq_id = get_model("sequence").find_sequence(type="tax_no")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            if exclude and num in exclude:
                get_model("sequence").increment_number(seq_id, context=context)
                continue
            res = get_model("account.move.line").search([["tax_no", "=", num], ["move_id.company_id", "=", company_id]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    def get_discount(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            subtotal=0
            disc = 0
            for line in obj.lines:
                subtotal+=(line.qty or 1)*(line.unit_price or 0)
                disc += (line.amount_discount or 0)
            vals[obj.id] = {
                "amount_subtotal_no_discount": subtotal,
                "amount_discount": disc,
            }
        return vals

    def create_fixed_assets(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.fixed_assets:
                raise Exception("Fixed assets already created for invoice %s" % obj.number)
            for line in obj.lines:
                acc = line.account_id
                if acc.type != "fixed_asset":
                    continue
                ass_type = acc.fixed_asset_type_id
                if not ass_type:
                    continue
                vals = {
                    "name": line.description,
                    "type_id": ass_type.id,
                    "date_purchase": obj.date,
                    "price_purchase": line.amount,  # XXX: should be tax-ex
                    "fixed_asset_account_id": acc.id,
                    "dep_rate": ass_type.dep_rate,
                    "dep_method": ass_type.dep_method,
                    "accum_dep_account_id": ass_type.accum_dep_account_id.id,
                    "dep_exp_account_id": ass_type.dep_exp_account_id.id,
                    "invoice_id": obj.id,
                }
                get_model("account.fixed.asset").create(vals)

    def delete_alloc(self, context={}):
        alloc_id = context["alloc_id"]
        get_model("account.credit.alloc").delete([alloc_id])

    def onchange_date(self, context={}):
        data = context["data"]
        ctx = {
            "type": data["type"],
            "inv_type": data["inv_type"],
            "date": data["date"],
        }
        if not data.get("id"):
            number = self._get_number(context=ctx)
            data["number"] = number
        if data.get("pay_term_id"):
            data=self.onchange_pay_term(context)
        return data

    def check_related(self, ids, context={}):
        obj = self.browse(ids)[0]
        rel = obj.related_id
        if not rel:
            return
        # if rel._model=="job": # XXX: doesn't work for bkkbase modules
        #    if not rel.done_approved_by_id:
        #        raise Exception("Service order has to be approved before it is invoiced")

    def get_template_invoice_form(self, ids=None, context={}):
        if ids is None:  # XXX: for backward compat with old templates
            ids = context["ids"]
        obj = get_model("account.invoice").browse(ids)[0]
        if obj.type == "out":
            if obj.amount_discount:
                return "cust_invoice_form_disc"
            else:
                return "cust_invoice_form"
        elif obj.type == "in":
            return "supp_invoice_form"

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

    def onchange_sequence(self, context={}):
        data = context["data"]
        seq_id = data["sequence_id"]
        num = self._get_number(context={"type": data["type"], "inv_type": data["inv_type"], "date": data["date"], "sequence_id": seq_id})
        data["number"] = num
        return data

    def pay_online(self,ids,context={}):
        obj=self.browse(ids[0])
        method=obj.pay_method_id
        if not method:
            raise Exception("Missing payment method for invoice %s"%obj.number)
        ctx={
            "amount": obj.amount_total,
            "currency_id": obj.currency_id.id,
            "details": "Invoice %s"%obj.number,
        }
        res=method.start_payment(context=ctx)
        if not res:
            raise Exception("Failed to start online payment for payment method %s"%method.name)
        transaction_no=res["transaction_no"]
        obj.write({"transaction_no":transaction_no})
        return {
            "next": res["payment_action"],
        }

    def get_payment_entries(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            line_ids=[]
            if obj.move_id:
                inv_line=obj.move_id.lines[0]
                rec=inv_line.reconcile_id
                if rec:
                    for line in rec.lines:
                        if line.id!=inv_line.id:
                            line_ids.append(line.id)
            vals[obj.id]=line_ids
        return vals

    def onchange_pay_term(self, context):
        data = context["data"]
        inv_date=data.get("date")
        pay_term_id = data.get("pay_term_id")
        if not pay_term_id:
            return {}
        pay_term=get_model("payment.term").browse(pay_term_id)
        if pay_term.days:
            d=datetime.strptime(inv_date,"%Y-%m-%d")
            d+=timedelta(days=pay_term.days)
            data["due_date"]=d.strftime("%Y-%m-%d")
        return data

    def get_product_type(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            prod_type="product"
            if obj.lines:
                prod=obj.lines[0].product_id
                if prod and prod.type=="service":
                    prod_type="service"
            vals[obj.id]=prod_type
        return vals

    def add_missing_accounts(self,ids,context={}):
        for obj in self.browse(ids):
            for line in obj.lines:
                if line.account_id:
                    continue
                prod=line.product_id
                if not prod:
                    continue
                if obj.type=="out":
                    acc_id=prod.sale_account_id.id
                    tax_id=prod.sale_tax_id.id
                elif obj.type=="in":
                    acc_id=prod.purchase_account_id.id
                    tax_id=prod.purchase_tax_id.id
                line.write({"account_id":acc_id,"tax_id":tax_id})

    def get_credit_orig_invoice(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            orig_inv=None
            for line in obj.payment_entries:
                move=line.move_id
                inv=move.related_id
                if inv._model!="account.invoice":
                    continue
                orig_inv=inv
            vals[obj.id]=orig_inv.id if orig_inv else None
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

    def copy_to_bill_note(self,ids,context={}):
        cust_invs={}
        for obj in self.browse(ids):
            if obj.bill_note_id:
                raise Exception("Billing note already created for invoice %s"%obj.number)
            if obj.type!="out":
                raise Exception("Invalid invoice type: %s"%obj.number)
            if obj.state!="waiting_payment":
                raise Exception("Invoice is not waiting payment: %s"%obj.number)
            cust_invs.setdefault(obj.contact_id.id,[]).append(obj)
        if not cust_invs:
            raise Exception("No billings notes to create")
        for cust_id,invs in cust_invs.items():
            vals={
                "customer_id": cust_id,
            }
            bill_id=get_model("bill.note").create(vals)
            for inv in invs:
                if inv.bill_id:
                    raise Exception("Billing note already created for invoice %s"%inv.number)
                inv.write({"bill_note_id": bill_id})
        return {
            "next": {
                "name": "bill_note",
            },
            "alert": "%d billing notes created"%len(cust_invs),
        }

    def get_total_qty(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            qty=0
            for line in obj.lines:
                qty+=line.qty or 0
            vals[obj.id]=qty
        return vals

    def get_amount_total_words(self,ids,context={}):
        vals={}
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

    def get_price_ship(self,ids,context={}): # XXX: replace by print template formulas?
        vals={}
        for obj in self.browse(ids):
            if obj.ship_term_id:
                diff=obj.ship_term_id.unit_price_diff or 0
                diff_percent=obj.ship_term_id.unit_price_diff_percent or 0
            else:
                diff=0
                diff_percent=0
            total=obj.amount_total*(1+diff_percent/Decimal(100))+diff*(obj.total_qty or 0)
            vals[obj.id]={
                "amount_total_ship": total,
                "amount_total_words_ship": utils.num2words(int(total)).upper(),
            }
        return vals

    def expenses_per_supplier(self, context={}):
        db = database.get_connection()
        res = db.query(
            "SELECT c.name,SUM(i.amount_total) as amount FROM account_invoice i,contact c WHERE c.id=i.contact_id AND i.state in ('waiting_payment','paid') GROUP BY c.name ORDER BY amount DESC")
        data = []
        for r in res:
            data.append((r.name, r.amount))
        return data

    def expenses_per_project(self, context={}):
        db = database.get_connection()
        res = db.query(
            "SELECT c.name,SUM(l.debit-l.credit) as amount FROM account_move m,account_move_line l,account_track_categ c WHERE m.id=l.move_id AND c.id=l.track_id AND m.state='posted' GROUP BY c.name ORDER BY amount DESC")
        data = []
        for r in res:
            data.append((r.name, r.amount))
        return data

    def create_next_invoice(self, ids, context={}):
        n=0
        for obj in self.browse(ids):
            if obj.state!="repeat":
                raise Exception("Invoice is not repeating")
            if not obj.next_date:
                continue
            vals={
                "inv_type": "invoice",
                "date": obj.next_date,
                "due_date": obj.next_due_date,
                "template_id": obj.id,
            }
            obj.copy(vals)
            d=datetime.strptime(obj.next_date,"%Y-%m-%d")
            if not obj.interval_num:
                raise Exception("Missing interval number")
            if obj.interval_unit=="day":
                d+=timedelta(days=obj.interval_num)
            elif obj.interval_unit=="month":
                d+=relativedelta(months=obj.interval_num)
            elif obj.interval_unit=="year":
                d+=relativedelta(years=obj.interval_num)
            else:
                raise Exception("Invalid interval unit")
            obj.write({"next_date":d.strftime("%Y-%m-%d")})
            if obj.next_due_date:
                d=datetime.strptime(obj.next_due_date,"%Y-%m-%d")
                if not obj.interval_num:
                    raise Exception("Missing interval number")
                if obj.interval_unit=="day":
                    d+=timedelta(days=obj.interval_num)
                elif obj.interval_unit=="month":
                    d+=relativedelta(months=obj.interval_num)
                elif obj.interval_unit=="year":
                    d+=relativedelta(years=obj.interval_num)
                else:
                    raise Exception("Invalid interval unit")
                obj.write({"next_due_date":d.strftime("%Y-%m-%d")})
            n+=1
        return {
            "alert": "%d invoices created"%n,
        }

    def create_repeating_all(self,context={}):
        t=time.strftime("%Y-%m-%d")
        for obj in self.search_browse([["state","=","repeat"],["next_date","<=",t]]):
            obj.create_next_invoice()

    def copy_to_supp_cust_invoice(self, ids, context={}):
        obj = self.browse(ids)[0]
        res=get_model("company").search([["contact_id","=",obj.contact_id.id]])
        if not res:
            raise Exception("Company not found for contact %s"%obj.contact_id.name)
        inv_company_id=res[0]
        related_id="%s,%s"%(obj.related_id._model,obj.related_id.id) if obj.related_id else None
        inv_vals = {
            "type": "out",
            "inv_type": obj.inv_type,
            "ref": obj.ref,
            "contact_id": obj.contact_id.id,
            "currency_id": obj.currency_id.id,
            "tax_type": obj.tax_type,
            "memo": obj.memo,
            "lines": [],
            "company_id": inv_company_id,
            "related_id": related_id,
        }
        company_id=access.get_active_company()
        access.set_active_company(inv_company_id)
        for line in obj.lines:
            prod=line.product_id
            line_vals = {
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
                "account_id": prod.sale_account_id.id if prod else None,
                "amount": line.amount,
                "related_id": related_id,
            }
            inv_vals["lines"].append(("create", line_vals))
        inv_id = self.create(inv_vals, context={"type": "out", "inv_type": obj.inv_type})
        inv = self.browse(inv_id)
        access.set_active_company(company_id)
        return {
            "flash": "Invoice %s copied successfully"%inv.number,
        }

    def copy_to_cust_supp_invoice(self, ids, context={}):
        obj = self.browse(ids)[0]
        res=get_model("company").search([["contact_id","=",obj.contact_id.id]])
        if not res:
            raise Exception("Company not found for contact %s"%obj.contact_id.name)
        inv_company_id=res[0]
        related_id="%s,%s"%(obj.related_id._model,obj.related_id.id) if obj.related_id else None
        inv_vals = {
            "type": "in",
            "sup_inv_number": obj.number,
            "inv_type": obj.inv_type,
            "ref": obj.ref,
            "contact_id": obj.contact_id.id,
            "currency_id": obj.currency_id.id,
            "tax_type": obj.tax_type,
            "memo": obj.memo,
            "lines": [],
            "company_id": inv_company_id,
            "related_id": related_id,
        }
        company_id=access.get_active_company()
        access.set_active_company(inv_company_id)
        for line in obj.lines:
            prod=line.product_id
            line_vals = {
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
                "account_id": prod.sale_account_id.id if prod else None,
                "amount": line.amount,
                "related_id": related_id,
            }
            inv_vals["lines"].append(("create", line_vals))
        inv_id = self.create(inv_vals, context={"type": "in", "inv_type": obj.inv_type})
        inv = self.browse(inv_id)
        access.set_active_company(company_id)
        return {
            "flash": "Invoice %s copied successfully"%inv.number,
        }

    def get_orig_invoice_amount_diff(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.orig_invoice_id:
                amt=obj.orig_invoice_id.amount_total-obj.amount_total
            else:
                amt=None
            vals[obj.id]=amt
        return vals

    def copy_to_pick_out(self, ids, context={}):
        id = ids[0]
        obj = self.browse(id)
        contact = obj.contact_id
        res = get_model("stock.location").search([["type", "=", "customer"]])
        if not res:
            raise Exception("Customer location not found")
        cust_loc_id = res[0]
        res = get_model("stock.location").search([["type", "=", "internal"]])
        if not res:
            raise Exception("Warehouse not found")
        wh_loc_id = res[0]
        pick_vals = {
            "type": "out",
            "ref": obj.number,
            "related_id": "account.invoice,%s" % obj.id,
            "contact_id": contact.id,
            "lines": [],
            "state": "draft",
            "company_id": obj.company_id.id,
        }
        for line in obj.lines:
            prod = line.product_id
            if not prod:
                continue
            if prod.type not in ("stock", "consumable", "bundle"):
                continue
            if line.qty <= 0:
                continue
            line_vals = {
                "product_id": prod.id,
                "qty": line.qty,
                "uom_id": prod.uom_id.id if line.qty_stock or not line.uom_id else line.uom_id.id,
                "location_from_id": wh_loc_id,
                "location_to_id": cust_loc_id,
                "invoice_id": obj.id,
            }
            pick_vals["lines"].append(("create", line_vals))
        if not pick_vals["lines"]:
            Exception("Nothing left to deliver")
        pick_id = get_model("stock.picking").create(pick_vals, context={"pick_type": "out"})
        return {
            "next": {
                "name": "pick_out",
                "mode": "form",
                "active_id": pick_id,
            },
            "flash": "Goods issue created from invoice %s" % obj.number,
        }

    def copy_to_pick_in(self, ids, context={}):
        id = ids[0]
        obj = self.browse(id)
        contact = obj.contact_id
        res = get_model("stock.location").search([["type", "=", "supplier"]])
        if not res:
            raise Exception("Supplier location not found")
        supp_loc_id = res[0]
        res = get_model("stock.location").search([["type", "=", "internal"]])
        if not res:
            raise Exception("Warehouse not found")
        wh_loc_id = res[0]
        pick_vals = {
            "type": "in",
            "ref": obj.number,
            "related_id": "account.invoice,%s" % obj.id,
            "contact_id": contact.id,
            "lines": [],
            "state": "draft",
            "company_id": obj.company_id.id,
        }
        for line in obj.lines:
            prod = line.product_id
            if not prod:
                continue
            if prod.type not in ("stock", "consumable", "bundle"):
                continue
            if line.qty <= 0:
                continue
            line_vals = {
                "product_id": prod.id,
                "qty": line.qty,
                "uom_id": prod.uom_id.id if line.qty_stock else line.uom_id.id,
                "location_from_id": supp_loc_id,
                "location_to_id": wh_loc_id,
                "invoice_id": obj.id,
            }
            pick_vals["lines"].append(("create", line_vals))
        if not pick_vals["lines"]:
            Exception("Nothing left to deliver")
        pick_id = get_model("stock.picking").create(pick_vals, context={"pick_type": "in"})
        return {
            "next": {
                "name": "pick_in",
                "mode": "form",
                "active_id": pick_id,
            },
            "flash": "Goods receipt created from invoice %s" % obj.number,
        }

    def get_total_weight(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            total_net_weight=0
            total_gross_weight=0
            for line in obj.lines:
                total_net_weight+=line.net_weight or 0
                total_gross_weight+=line.gross_weight or 0
            vals[obj.id]={
                "total_net_weight": total_net_weight,
                "total_gross_weight": total_gross_weight,
            }
        return vals

    def fix_conv_invoice(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.move_id:
            raise Exception("Journal entry already created")
        acc_id=obj.account_id.id
        if not acc_id:
            raise Exception("Missing invoice account")
        for line in obj.lines:
            if not line.account_id:
                line.write({"account_id":acc_id})
        move_vals={
            "number": obj.number,
            "date": obj.date,
            "narration": obj.memo,
            "lines": [],
        }
        line_vals={
            "description": obj.memo,
            "account_id": acc_id,
            "debit": obj.amount_total,
            "credit": 0,
        }
        move_vals["lines"].append(("create",line_vals))
        line_vals={
            "description": obj.memo,
            "account_id": acc_id,
            "debit": 0,
            "credit": obj.amount_total,
        }
        move_vals["lines"].append(("create",line_vals))
        move_id=get_model("account.move").create(move_vals)
        obj.write({"move_id":move_id})
        return {
            "flash": "Journal entry created",
        }

    def onchange_packaging(self, context):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        packaging_id = line.get("packaging_id")
        if not packaging_id:
            return {}
        packaging = get_model("stock.packaging").browse(packaging_id)
        if packaging.net_weight:
            line["net_weight"]=(line["qty"] or 0)*packaging.net_weight
        line["gross_weight"]=(line["net_weight"] or 0)+(line["qty"] or 0)*packaging.packaging_weight
        return data

    def get_pickings(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            pick_ids = []
            for move in obj.stock_moves:
                pick_id = move.picking_id.id
                pick_ids.append(pick_id)
            vals[obj.id] = list(set(pick_ids))
        return vals

    def copy_to_sale_old(self,ids,context={}):
        obj=self.browse(ids[0])
        purch=obj.related_id
        if not purch or purch._model!="purchase.order":
            raise Exception("Invoice must be linked to purchase order")
        if not purch.customer_id:
            raise Exception("Missing customer in purchase order")
        sale_vals={
            "contact_id": purch.customer_id.id,
            "ref": purch.number+" "+obj.number,
            "related_id": "purchase.order,%s"%purch.id,
            "lines": [],
        }
        for line in obj.lines:
            prod=line.product_id
            line_vals={
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": prod.sale_tax_id.id if prod else None,
            }
            sale_vals["lines"].append(("create",line_vals))
        sale_id=get_model("sale.order").create(sale_vals)
        sale=get_model("sale.order").browse(sale_id)
        return {
            "flash": "Sales order %s created from supplier invoice %s" % (sale.number, obj.number),
            "next": {
                "name": "sale",
                "mode": "form",
                "active_id": sale_id,
            },
        }

    def get_bill_index(self,ids,context={}):
        bill_ids=[]
        for obj in self.browse(ids):
            if obj.bill_note_id:
                bill_ids.append(obj.bill_note_id.id)
        bill_ids=list(set(bill_ids))
        vals={}
        for bill in get_model("bill.note").browse(bill_ids):
            i=1
            for inv in bill.invoices:
                if inv.id in ids:
                    vals[inv.id]=i
                i+=1
        return vals

    def get_sale(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.related_id and obj.related_id._model=="sale.order":
                sale_id=obj.related_id.id
            elif obj.lines and obj.lines[0].related_id and obj.lines[0].related_id._model=="sale.order":
                sale_id=obj.lines[0].related_id.id
            else:
                sale_id=None
            vals[obj.id]=sale_id
        return vals

    def get_picking(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            rel=obj.related_id
            if not rel:
                for line in obj.lines:
                    rel=line.related_id
                    if rel:
                        break
            pick_id=None
            if rel:
                if rel._model=="stock.picking":
                    pick_id=rel.id
                elif rel._model=="sale.order":
                    for pick in rel.pickings:
                        pick_id=pick.id
                        break
            vals[obj.id]=pick_id
        return vals

    def get_jc_job(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.related_id and obj.related_id._model=="jc.job":
                job_id=obj.related_id.id
            else:
                job_id=None
            vals[obj.id]=job_id
        return vals

    def get_time_total(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            hours=0
            amt=0
            for time in obj.time_entries:
                hours+=time.bill_hours or 0
                amt+=time.amount or 0
            vals[obj.id]={
                "total_bill_hours": hours,
                "total_bill_amount": amt,
            }
        return vals

    def get_time_users(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            user_ids=[]
            for t in obj.time_entries:
                if not t.user_id.code:
                    continue
                user_ids.append(t.user_id.id)
            user_ids=list(set(user_ids))
            vals[obj.id]=user_ids
        return vals

    def get_instructions(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            lines=[]
            if obj.pay_method_id and obj.pay_method_id.instructions:
                lines.append(obj.pay_method_id.instructions)
            for line in obj.lines:
                if line.tax_id and line.tax_id.instructions:
                    lines.append(line.tax_id.instructions)
            lines=list(set(lines))
            vals[obj.id]="\n".join(lines)
        return vals

    def get_cheque(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            cheque_id=None
            for line in obj.payments:
                pmt=line.payment_id
                if pmt.cheques:
                    cheque_id=pmt.cheques[0].id
                    break
            vals[obj.id]=cheque_id
        return vals

    def get_pay_flag(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            t=None
            for line in obj.payments:
                pmt=line.payment_id
                t=pmt.pay_method_id.type if pmt.pay_method_id else None
                if t:
                    break
            vals[obj.id]={
                "pay_cash": t=="cash",
                "pay_bank": t=="bank",
                "pay_cheque": t=="cheque",
            }
        return vals

    def copy_to_sale(self,ids,context={}):
        obj=self.browse(ids[0])
        vals={
            "contact_id": obj.contact_id.id,
            "ref": obj.number,
            "lines": [],
        }
        for line in obj.lines:
            line_vals={
                "product_id": line.product_id.id,
                "description": line.description,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "tax_id": line.tax_id.id,
            }
            vals["lines"].append(("create",line_vals))
        sale_id=get_model("sale.order").create(vals)
        sale=get_model("sale.order").browse(sale_id)
        return {
            "alert": "Sales order %s created"%sale.number,
            "next": {
                "name": "sale",
                "model": "form",
                "active_id": sale_id,
            },
        }

    def get_contact_categ(self,ids,context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id] = obj.contact_id.categ_id.id if obj.contact_id else None
        return vals

    def search_contact_categ(self, clause, context={}):
        categ_id = clause[2]
        cond = [["contact_id.categ_id","=",categ_id]]
        return cond
    

Invoice.register()
