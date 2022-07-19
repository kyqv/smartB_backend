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


class SaleQuotLine(Model):
    _name = "sale.quot.line"
    _fields = {
        "quot_id": fields.Many2One("sale.quot", "Quotation", required=True, on_delete="cascade", search=True),
        "product_id": fields.Many2One("product", "Product", search=True),
        "description": fields.Text("Description", required=True),
        "qty": fields.Decimal("Qty"),
        "uom_id": fields.Many2One("uom", "UoM"),
        "unit_price": fields.Decimal("Unit Price", scale=6),
        "discount": fields.Decimal("Disc %"),
        "tax_id": fields.Many2One("account.tax.rate", "Tax Rate"),
        "amount": fields.Decimal("Amount",function="get_amount"),
        "amount_discount": fields.Decimal("Discount Amount",function="get_amount_discount"),
        "contact_id": fields.Many2One("contact", "Contact", function="_get_related", function_search="_search_related", function_context={"path": "quot_id.contact_id"}, search=True),
        "date": fields.Date("Date", function="_get_related", function_search="_search_related", function_context={"path": "quot_id.date"}, search=True),
        "user_id": fields.Many2One("base.user", "Owner", function="_get_related", function_search="_search_related", function_context={"path": "quot_id.user_id"}, search=True),
        "state": fields.Selection([("draft", "Draft"), ("waiting_approval", "Awaiting Approval"), ("approved", "Approved"), ("won", "Won"), ("lost", "Lost"), ("revised", "Revised")], "Status", function="_get_related", function_search="_search_related", function_context={"path": "quot_id.state"}, search=True),
        "product_categs": fields.Many2Many("product.categ", "Product Categories", function="_get_related", function_context={"path": "product_id.categs"}, function_search="_search_related", search=True),
        "agg_amount": fields.Decimal("Total Amount", agg_function=["sum", "amount"]),
        "agg_qty": fields.Decimal("Total Order Qty", agg_function=["sum", "qty"]),
        "sequence": fields.Char("Item No.",function="get_sequence_old"), # XXX: deprecated
        "sequence_no": fields.Integer("Item No."),
        "index": fields.Integer("Index",function="get_index"),
        "cost_price": fields.Decimal("Cost Price"),
        "cost_amount": fields.Decimal("Cost Amount",function="get_profit",function_multi=True),
        "profit_amount": fields.Decimal("Profit Amount",function="get_profit",function_multi=True),
        "margin_percent": fields.Decimal("Margin %",function="get_profit",function_multi=True),
        "type": fields.Selection([["item","Item"],["group","Group"]],"Line Type"),
        "notes": fields.Text("Notes"),
        "amount_tax": fields.Decimal("Tax Amount",function="get_tax_amount",function_multi=True),
        "amount_incl_tax": fields.Decimal("Amount Including Tax",function="get_tax_amount",function_multi=True),
        "amount_excl_tax": fields.Decimal("Amount Excluding Tax",function="get_tax_amount",function_multi=True),
    }
    _order = "sequence_no,id"

    def get_sequence_old(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=str(obj.sequence_no)
        return vals

    def create(self, vals, context={}):
        id = super(SaleQuotLine, self).create(vals, context)
        self.function_store([id])
        return id

    def write(self, ids, vals, context={}):
        super(SaleQuotLine, self).write(ids, vals, context)
        self.function_store(ids)

    def get_amount(self, ids, context={}):
        vals={}
        for obj in self.browse(ids):
            amt=None
            if obj.unit_price and obj.qty:
                amt=obj.unit_price*obj.qty
                if obj.discount:
                    amt=amt*(1-obj.discount/100)
            vals[obj.id]=amt
        return vals

    def get_amount_discount(self, ids, context={}):
        vals={}
        for obj in self.browse(ids):
            disc=None
            if obj.unit_price and obj.qty and obj.discount:
                disc=obj.unit_price*obj.qty*obj.discount/100
            vals[obj.id]=disc
        return vals

    def get_profit(self, ids, context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.cost_price is not None:
                cost=obj.cost_price*(obj.qty or 0)
                profit=(obj.amount or 0)-cost
                margin=profit*100/obj.amount if obj.amount else None
            else:
                cost=None
                profit=None
                margin=None
            vals[obj.id]={
                "cost_amount": cost,
                "profit_amount": profit,
                "margin_percent": margin,
            }
        return vals

    def get_index(self,ids,context={}):
        quot_ids=[]
        for obj in self.browse(ids):
            quot_ids.append(obj.quot_id.id)
        quot_ids=list(set(quot_ids))
        vals={}
        for quot in get_model("sale.quot").browse(quot_ids):
            i=1
            for line in quot.lines:
                if line.id in ids:
                    vals[line.id]=i
                i+=1
        return vals

    def get_tax_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt_tax=0
            amt_incl=0
            amt_excl=0
            tax_id = obj.tax_id.id
            quot=obj.quot_id
            if tax_id and quot.tax_type != "no_tax" and obj.tax_id.rate:
                base_amt = get_model("account.tax.rate").compute_base(tax_id, obj.amount or 0, tax_type=quot.tax_type)
                tax_comps = get_model("account.tax.rate").compute_taxes(tax_id, base_amt, when="invoice")
                for comp_id, tax_amt in tax_comps.items():
                    amt_tax += tax_amt
            if quot.tax_type=="tax_ex":
                amt_excl=obj.amount or 0
                amt_incl=amt_excl+amt_tax
            elif quot.tax_type=="tax_in":
                amt_incl=obj.amount or 0
                amt_excl=amt_incl-amt_tax
            vals[obj.id]={
                "amount_tax": amt_tax,
                "amount_incl_tax": amt_incl,
                "amount_excl_tax": amt_excl,
            }
        return vals

SaleQuotLine.register()
