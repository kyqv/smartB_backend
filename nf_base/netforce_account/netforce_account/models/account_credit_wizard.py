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


class CreditWizard(Model):
    _name = "account.credit.wizard"
    _transient = True
    _fields = {
        "invoice_id": fields.Many2One("account.invoice", "Invoice", required=True, on_delete="cascade"),
        "type": fields.Char("Type"),
        "lines": fields.One2Many("account.credit.wizard.line", "wiz_id", "Lines"),
        "amount_due": fields.Decimal("Amount Due on Invoice", readonly=True),
        "amount_alloc": fields.Decimal("Total Amount to Credit", readonly=True),
        "amount_remain": fields.Decimal("Remaining Due", readonly=True),
    }

    def default_get(self, field_names={}, context={}, **kw):
        if "invoice_id" not in context:
            return {}
        inv_id = int(context["invoice_id"])
        inv = get_model("account.invoice").browse(inv_id)
        contact_id = inv.contact_id.id
        lines = []
        if inv.type=="out":
            cond=[["account_id.type","in",["receivable","cust_deposit"]],["credit","!=",0],["contact_id","=",contact_id],["move_id.state","=","posted"]]
        else:
            cond=[["account_id.type","in",["payable","sup_deposit"]],["debit","!=",0],["contact_id","=",contact_id],["move_id.state","=","posted"]]
        for move_line in get_model("account.move.line").search_browse(cond):
            move=move_line.move_id
            acc=move_line.account_id
            rec=move_line.reconcile_id
            if rec:
                amt=rec.balance
            else:
                amt=move_line.debit-move_line.credit
            if amt==0:
                continue
            if inv.type=="out":
                amt=-amt
            line_vals={
                "move_line_id": move_line.id,
                "move_id": [move.id,move.name_get()[0][1]],
                "date": move.date,
                "account_id": [acc.id,acc.name_get()[0][1]],
                "amount_credit_remain": amt,
            }
            lines.append(line_vals)
        vals = {
            "invoice_id": [inv.id, inv.name_get()[0][1]],
            "lines": lines,
            "type": inv.type,
            "amount_due": inv.amount_due,
            "amount_alloc": 0,
            "amount_remain": inv.amount_due,
        }
        return vals

    def allocate(self, ids, context={}):
        obj = self.browse(ids)[0]
        inv=obj.invoice_id
        if inv.inv_type != "invoice":
            raise Exception("Wrong invoice type")
        contact=inv.contact_id
        for line in obj.lines:
            if not line.amount:
                continue
            cred_move_line=line.move_line_id
            desc = "Credit allocation: %s" % contact.name
            move_vals={
                "journal_id": cred_move_line.move_id.journal_id.id, # XXX
                "date": obj.date,
                "narration": desc,
                "lines": [],
                "related_id": "account.invoice,%d"%inv.id,
            }
            move_id = get_model("account.move").create(move_vals)
            if inv.type == "in":
                sign = 1
            else:
                sign = -1
            amt=line.amount*sign # TODO: currency convert
            line_vals={
                "move_id": move_id,
                "description": desc,
                "account_id": inv.account_id.id,
                "debit": amt > 0 and amt or 0,
                "credit": amt < 0 and -amt or 0,
                "contact_id": contact.id,
            }
            line1_id=get_model("account.move.line").create(line_vals)
            line_vals={
                "move_id": move_id,
                "description": desc,
                "account_id": cred_move_line.account_id.id,
                "debit": amt < 0 and -amt or 0,
                "credit": amt > 0 and amt or 0,
                "contact_id": contact.id,
            }
            line2_id=get_model("account.move.line").create(line_vals)
            get_model("account.move").post([move_id])
            if not inv.move_id or not inv.move_id.lines:
                raise Exception("Failed to find invoice journal entry line to reconcile")
            inv_line_id=inv.move_id.lines[0].id
            get_model("account.move.line").reconcile([inv_line_id,line1_id])
            get_model("account.move.line").reconcile([cred_move_line.id,line2_id])
        return {
            "next": {
                "name": "view_invoice",
                "active_id": obj.invoice_id.id,
            },
            "flash": "Invoice updated.",
        }

    def update_amounts(self, context={}):
        data = context["data"]
        amt = 0
        for line in data["lines"]:
            amt += line.get("amount", 0)
        data["amount_alloc"] = amt
        data["amount_remain"] = data["amount_due"] - amt
        return data

CreditWizard.register()
