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


class PaymentLine(Model):
    _name = "account.payment.line"
    _string = "Payment Line"
    _fields = {
        "payment_id": fields.Many2One("account.payment", "Payment", required=True, on_delete="cascade"),
        "type": fields.Selection([["direct", "Direct Payment"], ["invoice", "Invoice Payment"], ["refund", "Refund"], ["prepay", "Prepayment"], ["overpay", "Overpayment"], ["claim", "Expense Claim Payment"], ["adjust","Adjustment"]], "Type", required=True),
        "description": fields.Text("Description"),
        "qty": fields.Decimal("Qty"),
        "unit_price": fields.Decimal("Unit Price"),
        "account_id": fields.Many2One("account.account", "Account", condition=[["type", "!=", "view"]]),
        "tax_id": fields.Many2One("account.tax.rate", "Tax Rate"),
        "amount": fields.Decimal("Paid Amount (Pmt Cur)", required=True, scale=4), # XXX: KFF
        "invoice_id": fields.Many2One("account.invoice", "Invoice"),
        "expense_id": fields.Many2One("expense.claim", "Expense Claim"),
        "track_id": fields.Many2One("account.track.categ", "Track-1", condition=[["type", "=", "1"]]),
        "track2_id": fields.Many2One("account.track.categ", "Track-2", condition=[["type", "=", "2"]]),
        "tax_comp_id": fields.Many2One("account.tax.component", "Tax Comp."),
        "tax_base": fields.Decimal("Tax Base"),
        "tax_no": fields.Char("Tax No."),
        "tax_date": fields.Date("Tax Invoice Date"),
        "amount_invoice": fields.Decimal("Paid Amount (Inv Cur)"),
        "invoice_currency_id": fields.Many2One("currency", "Invoice Currency", function="_get_related", function_context={"path": "invoice_id.currency_id"}),
        "invoice_amount_due": fields.Decimal("Due Amount", function="_get_related", function_context={"path": "invoice_id.amount_due"}),
        "currency_rate": fields.Decimal("Currency Rate (Pmt->Inv)"),
        "product_id": fields.Many2One("product","Product"),
        "contact_id": fields.Many2One("contact", "Contact"),
        "amount_company": fields.Decimal("Paid Amount (Company Cur)"),
        "index": fields.Integer("Index",function="get_index"),
    }

    def create(self, vals, context={}):
        pmt_id = vals["payment_id"]
        pmt = get_model("account.payment").browse(pmt_id)
        if pmt.pay_type == "direct":
            vals["type"] = "direct"
        elif pmt.pay_type == "prepay":
            vals["type"] = "prepay"
        elif pmt.pay_type == "overpay":
            vals["type"] = "overpay"
        elif pmt.pay_type == "invoice":
            if vals.get("invoice_id"):  # XXX
                vals["type"] = "invoice"
            else:
                vals["type"] = "adjust"
        elif pmt.pay_type == "claim":
            vals["type"] = "claim"
        new_id = super().create(vals, context=context)
        return new_id

    # XXX: remove this
    def get_amount_currency(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            pmt = obj.payment_id
            if pmt.type == "in":
                rate_type = "sell"
            else:
                rate_type = "buy"
            inv = obj.invoice_id
            if inv:
                amt = get_model("currency").convert(
                    obj.amount, pmt.currency_id.id, inv.currency_id.id, date=pmt.date, rate_type=rate_type)
            else:
                amt = None
            vals[obj.id] = amt
        return vals

    def get_index(self,ids,context={}):
        pmt_ids=[]
        for obj in self.browse(ids):
            pmt_ids.append(obj.payment_id.id)
        pmt_ids=list(set(pmt_ids))
        vals={}
        for pmt in get_model("account.payment").browse(pmt_ids):
            i=1
            for line in pmt.lines:
                if line.id in ids:
                    vals[line.id]=i
                i+=1
        return vals

PaymentLine.register()
