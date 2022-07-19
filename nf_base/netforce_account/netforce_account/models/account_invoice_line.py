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
from decimal import *


class InvoiceLine(Model):
    _name = "account.invoice.line"
    _string="Invoice Line"
    _fields = {
        "sequence": fields.Char("Sequence"), # XXX: deprecated
        "sequence_no": fields.Integer("Item No."),
        "invoice_id": fields.Many2One("account.invoice", "Invoice", required=True, on_delete="cascade"),
        "product_id": fields.Many2One("product", "Product",search=True),
        "description": fields.Text("Description", required=True),
        "qty": fields.Decimal("Qty"),
        "qty2": fields.Decimal("Qty2"),
        "uom_id": fields.Many2One("uom", "UoM"),
        "uom2_id": fields.Many2One("uom", "UoM2"),
        "unit_price": fields.Decimal("Unit Price", scale=6),
        "discount": fields.Decimal("Disc %"),  # XXX: rename to discount_percent later
        "discount_amount": fields.Decimal("Disc Amt"),
        "account_id": fields.Many2One("account.account", "Account", condition=[["type", "!=", "view"]]),
        "tax_id": fields.Many2One("account.tax.rate", "Tax Rate", on_delete="restrict"),
        "amount": fields.Decimal("Amount", required=True),
        "invoice_date": fields.Date("Invoice Date", function="_get_related", function_search="_search_related", function_context={"path": "invoice_id.date"}, search=True),
        "invoice_contact_id": fields.Many2One("contact", "Invoice Partner", function="_get_related", function_context={"path": "invoice_id.contact_id"}),
        "invoice_state": fields.Selection([("draft", "Draft"), ("waiting_approval", "Waiting Approval"), ("waiting_payment", "Waiting Payment"), ("paid", "Paid"), ("voided", "Voided"), ("repeat","Repeating")], "Status", function="_get_related", function_search="_search_related", search=True, function_context={"path": "invoice_id.state"}),
        "purch_id": fields.Many2One("purchase.order", "Purchase Order"),
        "track_id": fields.Many2One("account.track.categ", "Track-1", condition=[["type", "=", "1"]]),
        "track2_id": fields.Many2One("account.track.categ", "Track-2", condition=[["type", "=", "2"]]),
        "amount_discount": fields.Decimal("Discount", function="get_discount", function_multi=True),
        "amount_before_discount": fields.Decimal("Amount Before Discount", function="get_discount", function_multi=True),
        "related_id": fields.Reference([["sale.order", "Sales Order"], ["purchase.order", "Purchase Order"], ["production.order","Production Order"], ["project", "Project"], ["job", "Service Order"], ["service.contract", "Service Contract"], ["work.time","Work Time"]], "Related To"),
        "sale_id": fields.Many2One("sale.order", "Sale Order"),
        "purchase_id": fields.Many2One("purchase.order","Purchase Order"),
        "track_distrib_id": fields.Many2One("track.distrib","Tracking Distribution"),
        "unit_price_ship": fields.Decimal("Unit Price (Ship)",function="get_price_ship",function_multi=True), # XXX
        "amount_ship": fields.Decimal("Amount (Ship)",function="get_price_ship",function_multi=True), # XXX
        "index": fields.Integer("Index",function="get_index"),
        "notes": fields.Text("Notes"),
        "net_weight": fields.Decimal("Net Weight",scale=3),
        "packaging_id": fields.Many2One("stock.packaging","Packaging"),
        "gross_weight": fields.Decimal("Gross Weight",scale=3),
        "amount_tax": fields.Decimal("Tax Amount",function="get_tax_amount",function_multi=True),
        "amount_incl_tax": fields.Decimal("Amount Including Tax",function="get_tax_amount",function_multi=True),
        "amount_excl_tax": fields.Decimal("Amount Excluding Tax",function="get_tax_amount",function_multi=True),
    }
    _order="sequence_no,id"

    def create(self, vals, **kw):
        id = super(InvoiceLine, self).create(vals, **kw)
        self.update_amounts([id])
        sale_id = vals.get("sale_id")
        if sale_id:
            get_model("sale.order").function_store([sale_id])
        purch_id = vals.get("purch_id")
        if purch_id:
            get_model("purchase.order").function_store([purch_id])
        return id

    def write(self, ids, vals, context={}, **kw):
        sale_ids = []
        purch_ids = []
        for obj in self.browse(ids):
            if obj.sale_id:
                sale_ids.append(obj.sale_id.id)
            if obj.purch_id:
                purch_ids.append(obj.purch_id.id)
        super(InvoiceLine, self).write(ids, vals, **kw)
        if not context.get("no_update_amounts"):
            self.update_amounts(ids)
        sale_id = vals.get("sale_id")
        if sale_id:
            sale_ids.append(sale_id)
        purch_id = vals.get("purch_id")
        if purch_id:
            purch_ids.append(purch_id)
        if sale_ids:
            get_model("sale.order").function_store(sale_ids)
        if purch_ids:
            get_model("purchase.order").function_store(purch_ids)

    def delete(self, ids, **kw):
        sale_ids = []
        purch_ids = []
        for obj in self.browse(ids):
            if obj.sale_id:
                sale_ids.append(obj.sale_id.id)
            if obj.purch_id:
                purch_ids.append(obj.purch_id.id)
        super(InvoiceLine, self).delete(ids, **kw)
        if sale_ids:
            get_model("sale.order").function_store(sale_ids)
        if purch_ids:
            get_model("purchase.order").function_store(purch_ids)

    def get_discount(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            amt = (obj.qty or 0) * (obj.unit_price or 0)
            disc = 0
            if obj.discount:
                disc += amt * obj.discount / 100
            if obj.discount_amount:
                disc += obj.discount_amount
            vals[obj.id] = {
                "amount_discount": disc,
                "amount_before_discount": amt,
            }
        return vals

    def get_price_ship(self,ids,context={}): # XXX: replace by print template formulas?
        vals={}
        for obj in self.browse(ids):
            inv=obj.invoice_id
            if inv.ship_term_id:
                diff=inv.ship_term_id.unit_price_diff or 0
                diff_percent=inv.ship_term_id.unit_price_diff_percent or 0
            else:
                diff=0
                diff_percent=0
            vals[obj.id]={
                "unit_price_ship": (obj.unit_price*(1+diff_percent/Decimal(100)))+diff,
                "amount_ship": (obj.amount*(1+diff_percent/Decimal(100)))+diff*(obj.qty or 0),
            }
        return vals

    def get_index(self,ids,context={}):
        inv_ids=[]
        for obj in self.browse(ids):
            inv_ids.append(obj.invoice_id.id)
        inv_ids=list(set(inv_ids))
        vals={}
        for inv in get_model("account.invoice").browse(inv_ids):
            i=1
            for line in inv.lines:
                if line.id in ids:
                    vals[line.id]=i
                i+=1
        return vals

    def get_gross_weight(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            w=obj.net_weight or 0
            if obj.packaging_id:
                w+=(obj.packaging_id.packaging_weight or 0)*(obj.qty or 0)
            vals[obj.id]=w
        return vals

    def view_invoice_line(self,ids,context={}):
        obj=self.browse(ids[0])
        return obj.invoice_id.view_invoice(context=context)

    def update_amounts(self,ids,context={}):
        for obj in self.browse(ids):
            if obj.unit_price is None:
                continue
            amt = (obj.qty or 0) * (obj.unit_price or 0)
            if obj.discount:
                disc = amt * obj.discount / 100
                amt -= disc
            if obj.discount_amount:
                amt -= obj.discount_amount
            obj.write({"amount":amt},context={"no_update_amounts":True})

    def get_tax_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt_tax=0
            amt_incl=0
            amt_excl=0
            tax_id = obj.tax_id.id
            inv=obj.invoice_id
            if tax_id and inv.tax_type != "no_tax" and obj.tax_id.rate:
                base_amt = get_model("account.tax.rate").compute_base(tax_id, obj.amount, tax_type=inv.tax_type)
                tax_comps = get_model("account.tax.rate").compute_taxes(tax_id, base_amt, when="invoice")
                for comp_id, tax_amt in tax_comps.items():
                    amt_tax += tax_amt
            if inv.tax_type=="tax_ex":
                amt_excl=obj.amount
                amt_incl=amt_excl+amt_tax
            elif inv.tax_type=="tax_in":
                amt_incl=obj.amount
                amt_excl=amt_incl-amt_tax
            vals[obj.id]={
                "amount_tax": amt_tax,
                "amount_incl_tax": amt_incl,
                "amount_excl_tax": amt_excl,
            }
        return vals

InvoiceLine.register()
