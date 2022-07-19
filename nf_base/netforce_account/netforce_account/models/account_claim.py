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
import uuid


class Claim(Model):
    _name = "account.claim"
    _name_field = "number"
    _fields = {
        "number": fields.Char("Number"),
        "user_id": fields.Many2One("base.user", "Claim Owner", readonly=True),
        "date": fields.Date("Date Submitted", readonly=True),
        "due_date": fields.Date("Payment Due Date"),
        "amount_total": fields.Decimal("Total", function="get_amount", function_multi=True, store=True),
        "amount_approved": fields.Decimal("Approved Total", function="get_amount", function_multi=True, store=True),
        "amount_paid": fields.Decimal("Amount Paid", function="get_amount", function_multi=True, store=True),
        "amount_due": fields.Decimal("Amount Due", function="get_amount", function_multi=True, store=True),
        "state": fields.Selection([("waiting_approval", "Waiting Approval"), ("waiting_payment", "Waiting Payment"), ("paid", "Paid"), ("voided", "Voided")], "Status", function="get_state", store=True, function_order=20),
        "expenses": fields.One2Many("account.expense", "claim_id", "Receipts"),
        "payments": fields.One2Many("account.payment.line", "claim_id", "Payments"),
        "num_receipts": fields.Integer("Receipts", function="get_num_receipts"),
        "can_authorize": fields.Boolean("Can Authorize", function="get_can_authorize"),
        "uuid": fields.Char("UUID"),
        "move_id": fields.Many2One("account.move", "Journal Entry"),
        "account_id": fields.Many2One("account.account", "Account"),
    }
    _defaults = {
        "state": "waiting_approval",
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "uuid": lambda *a: str(uuid.uuid4()),
    }

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            name = obj.number
            if not name:  # XXX
                name = "Claim"
            vals.append((obj.id, name))
        return vals

    def create(self, vals, **kw):
        id = super().create(vals, **kw)
        self.function_store([id])
        return id

    def write(self, ids, vals, **kw):
        super().write(ids, vals, **kw)
        self.function_store(ids)

    def delete(self, ids, **kw):
        payment_ids = []
        for obj in self.browse(ids):
            if obj.move_id:
                obj.move_id.delete()
            for line in obj.payments:
                payment_ids.append(line.payment_id.id)
        payment_ids = list(set(payment_ids))
        get_model("account.payment").delete(payment_ids)
        super().delete(ids, **kw)

    def get_amount(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            total = 0
            approved = 0
            for exp in obj.expenses:
                total += exp.amount_total
                if exp.state == "approved":
                    approved += exp.amount_total
            paid = 0
            for line in obj.payments:
                paid += line.amount
            vals[obj.id] = {
                "amount_total": total,
                "amount_approved": approved,
                "amount_paid": paid,
                "amount_due": approved - paid,
            }
        return vals

    def get_state(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            state = obj.state
            if state == "waiting_payment" and obj.amount_due == 0:
                state = "paid"
            elif state == "paid" and obj.amount_due > 0:
                state = "waiting_payment"
            vals[obj.id] = state
        return vals

    def get_num_receipts(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id] = len(obj.expenses)
        return vals

    def get_can_authorize(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            can_authorize = True
            for exp in obj.expenses:
                if exp.state not in ("approved", "declined"):
                    can_authorize = False
            vals[obj.id] = can_authorize
        return vals

    def do_authorize(self, ids, context={}):
        obj = self.browse(ids)[0]
        assert obj.due_date, "Missing payment due date"
        obj.post()
        obj.write({"state": "waiting_payment"})
        return {
            "next": {
                "name": "claim_waiting_payment",
            }
        }

    def void(self, ids, context={}):
        obj = self.browse(ids)[0]
        assert not obj.payments, "This claim is already paid"
        if obj.move_id:
            obj.move_id.delete()
        obj.write({"state": "voided"})

    def post(self, ids, context={}):
        obj = self.browse(ids)[0]
        settings = get_model("settings").browse(1)
        claim_account_id = settings.unpaid_claim_id.id
        assert claim_account_id, "Missing unpaid expense claims account"
        obj.write({"account_id": claim_account_id})
        desc = "Claim: %s" % obj.number
        journal_id = settings.general_journal_id.id
        if not journal_id:
            raise Exception("General journal not found")
        move_vals = {
            "journal_id": journal_id,
            "date": obj.date,
            "narration": desc,
            "related_id": "account.claim,%s" % obj.id,
        }
        lines = []
        line_vals = {
            "description": desc,
            "account_id": claim_account_id,
            "credit": obj.amount_approved,
        }
        lines.append(line_vals)
        accounts = {}
        for exp in obj.expenses:
            if exp.state != "approved":
                continue
            for line in exp.lines:
                tax_amt = 0
                if line.tax_id:
                    tax_comps = get_model("account.tax.rate").compute_components(
                        line.tax_id.id, line.amount, tax_type=exp.tax_type)
                    for comp_id, comp_amt in tax_comps.items():
                        comp = get_model("account.tax.component").browse(comp_id)
                        account_id = comp.account_id.id
                        accounts[account_id] = accounts.get(account_id, 0) + comp_amt
                        tax_amt += comp_amt
                amt = line.amount
                if exp.tax_type == "tax_in":
                    amt -= tax_amt
                account_id = line.account_id.id
                accounts[account_id] = accounts.get(account_id, 0) + amt
        for acc_id, amt in accounts.items():
            line_vals = {
                "account_id": acc_id,
                "description": desc,
                "debit": amt,
            }
            lines.append(line_vals)
        # XXX: tax recording
        move_vals["lines"] = [("create", vals) for vals in lines]
        move_id = get_model("account.move").create(move_vals)
        get_model("account.move").post([move_id])
        obj.write({"move_id": move_id})

Claim.register()
