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


class InvoiceOverpay(Model):
    _name = "invoice.overpay"
    _transient = True
    _fields = {
        "payment_id": fields.Many2One("account.payment", "Payment", required=True, on_delete="cascade"),
        "amount_overpay": fields.Decimal("Amount", readonly=True),
        "description": fields.Char("Description"),
    }

    def _get_payment(self, context={}):
        pmt_id = int(context["payment_id"])
        return pmt_id

    def _get_amount(self, context={}):
        pmt_id = int(context["payment_id"])
        pmt = get_model("account.payment").browse(pmt_id)
        if pmt.pay_type != "invoice":
            raise Exception("Wrong payment type")
        amt_over = 0
        for line in pmt.invoice_lines:
            amt_over += max(0, line.amount_invoice - line.invoice_id.amount_due)
        return amt_over

    _defaults = {
        "payment_id": _get_payment,
        "amount_overpay": _get_amount,
    }

    def do_overpay(self, ids, context={}):
        obj = self.browse(ids)[0]
        pmt = obj.payment_id
        pmt.post(context={"overpay_description": obj.description})
        return {
            "next": {
                "name": "payment",
                "mode": "form",
                "active_id": pmt.id,
            }
        }

InvoiceOverpay.register()
