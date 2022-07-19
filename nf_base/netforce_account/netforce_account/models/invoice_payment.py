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
import time

class InvoicePayment(Model):
    _name = "invoice.payment"
    _transient = True
    _fields = {
        "amount": fields.Decimal("Amount", required=True),
        "amount_overpay": fields.Decimal("Amount", function="get_overpay"),
        "date": fields.Date("Date", required=True),
        "account_id": fields.Many2One("account.account", "Account", required=True, condition=["or", ["type", "in", ["bank","cash","cheque"]], ["enable_payment", "=", True]], on_delete="cascade"),
        "track_id": fields.Many2One("account.track.categ", "Tracking", on_delete="cascade"),
        "ref": fields.Char("Ref"),
        "invoice_id": fields.Many2One("account.invoice", "Invoice", required=True, on_delete="cascade"),
        "description": fields.Char("Description"),
    }

    def _get_invoice(self, context={}):
        return context["parent_id"]

    _defaults = {
        "invoice_id": _get_invoice,
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    def get_overpay(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            obj.id: obj.amount - obj.invoice_id.amount_due,
        }
        return vals

    def add_payment(self, ids, context={}):
        obj = self.browse(ids)[0]
        inv = obj.invoice_id
        if inv.inv_type not in ("invoice", "debit"):
            raise Exception("Wrong invoice type")
        if obj.amount > inv.amount_due:
            raise Exception("Amount paid exceeds due amount")
        vals = {
            "type": inv.type == "out" and "in" or "out",
            "pay_type": "invoice",
            "contact_id": inv.contact_id.id,
            "date": obj.date,
            "ref": obj.ref,
            "account_id": obj.account_id.id,
            "track_id": obj.track_id.id,
            "currency_id": inv.currency_id.id,
            "lines": [("create", {
                "type": "invoice",
                "invoice_id": inv.id,
                "account_id": inv.account_id.id,
                "amount": obj.amount,
            })],
        }
        pmt_id = get_model("account.payment").create(vals, context={"type": vals["type"]})
        get_model("account.payment").post([pmt_id])
        return {
            "next": {
                "name": "view_invoice",
                "active_id": inv.id,
            }
        }

InvoicePayment.register()
