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
import time
import uuid


class Expense(Model):
    _name = "account.expense"
    _name_field = "ref"
    _fields = {
        "contact_id": fields.Many2One("contact", "Contact", required=True),
        "date": fields.Date("Date", required=True),
        "ref": fields.Char("Reference", required=True),
        "attach": fields.File("Attachment"),
        "tax_type": fields.Selection([["tax_ex", "Tax Exclusive"], ["tax_in", "Tax Inclusive"], ["no_tax", "No Tax"]], "Tax Type", required=True),
        "lines": fields.One2Many("account.expense.line", "expense_id", "Lines"),
        "amount_subtotal": fields.Decimal("Subtotal", function="get_amount", function_multi=True),
        "amount_tax": fields.Decimal("Tax Amount", function="get_amount", function_multi=True),
        "amount_total": fields.Decimal("Total", function="get_amount", function_multi=True),
        "claim_id": fields.Many2One("account.claim", "Claim", on_delete="cascade"),
        "user_id": fields.Many2One("base.user", "Receipt Owner", required=True),
        "state": fields.Selection([["draft", "Draft"], ["waiting_approval", "Waiting Approval"], ["approved", "Approved"], ["declined", "Declined"]], "Status", required=True),
        "uuid": fields.Char("UUID"),
    }
    _order = "date desc,id desc"
    _defaults = {
        "tax_type": "tax_in",
        "uuid": lambda *a: str(uuid.uuid4()),
        "user_id": lambda self, context: int(context["user_id"]),
        "state": "draft",
    }

    def write(self, ids, vals, **kw):
        claim_ids = []
        for obj in self.browse(ids):
            if obj.claim_id:
                claim_ids.append(obj.claim_id.id)
        super().write(ids, vals, **kw)
        claim_id = vals.get("claim_id")
        if claim_id:
            claim_ids.append(claim_id)
        self.function_store(ids)
        if claim_ids:
            get_model("account.claim").function_store(claim_ids)

    def delete(self, ids, **kw):
        claim_ids = []
        for obj in self.browse(ids):
            if obj.claim_id:
                claim_ids.append(obj.claim_id.id)
        super().delete(ids, **kw)
        if claim_ids:
            get_model("account.claim").function_store(claim_ids)

    def get_amount(self, ids, context={}):  # XXX: taxes
        res = {}
        for obj in self.browse(ids):
            vals = {}
            subtotal = 0
            for line in obj.lines:
                subtotal += line.amount
            vals["amount_subtotal"] = subtotal
            vals["amount_tax"] = 0
            vals["amount_total"] = subtotal
            res[obj.id] = vals
        return res

    def update_amounts(self, context):
        data = context["data"]
        data["amount_subtotal"] = 0
        data["amount_tax"] = 0
        tax_type = data["tax_type"]
        for line in data["lines"]:
            if not line:
                continue
            amt = line.get("qty", 0) * line.get("unit_price", 0)
            line["amount"] = amt
            tax_id = line.get("tax_id")
            if tax_id:
                tax = get_model("account.tax.rate").compute_tax(tax_id, amt, tax_type=tax_type)
                data["amount_tax"] += tax
            else:
                tax = 0
            if tax_type == "tax_in":
                data["amount_subtotal"] += amt - tax
            else:
                data["amount_subtotal"] += amt
        data["amount_total"] = data["amount_subtotal"] + data["amount_tax"]
        return data

    def do_submit(self, ids, context={}):
        user_id = None
        for obj in self.browse(ids):
            if user_id is None:
                user_id = obj.user_id.id
            else:
                assert user_id == obj.user_id.id, "Expenses belong to different users"
        vals = {
            "user_id": user_id,
        }
        claim_id = get_model("account.claim").create(vals)
        self.write(ids, {"claim_id": claim_id, "state": "waiting_approval"})
        return {
            "next": {
                "name": "claim_waiting_approval"
            }
        }

    def do_approve(self, ids, context={}):
        claim_id = None
        for obj in self.browse(ids):
            obj.write({"state": "approved"})
            claim_id = obj.claim_id.id
        return {
            "next": {
                "name": "claim_edit",
                "active_id": claim_id,
            }
        }

    def do_decline(self, ids, context={}):
        claim_id = None
        for obj in self.browse(ids):
            obj.write({"state": "declined"})
            claim_id = obj.claim_id.id
        return {
            "next": {
                "name": "claim_edit",
                "active_id": claim_id,
            }
        }

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

Expense.register()
