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


class AllocWizard(Model):
    _name = "account.alloc.wizard"
    _transient = True
    _fields = {
        "credit_id": fields.Many2One("account.invoice", "Credit Note", required=True, on_delete="cascade"),
        "type": fields.Char("Type"),
        "lines": fields.One2Many("account.alloc.wizard.line", "wiz_id", "Lines"),
        "amount_credit": fields.Decimal("Outstanding Credit", readonly=True),
        "amount_alloc": fields.Decimal("Total Amount to Credit", readonly=True),
        "amount_remain": fields.Decimal("Remaining Credit", readonly=True),
    }

    def default_get(self, field_names={}, context={}, **kw):
        if "credit_id" not in context:
            return {}
        cred_id = int(context["credit_id"])
        cred = get_model("account.invoice").browse(cred_id)
        contact_id = cred.contact_id.id
        lines = []
        if cred.type=="out":
            cond=[["account_id.type","in",["receivable","cust_deposit"]],["debit","!=",0],["contact_id","=",contact_id],["move_id.state","=","posted"]]
        else:
            cond=[["account_id.type","in",["payable","sup_deposit"]],["credit","!=",0],["contact_id","=",contact_id],["move_id.state","=","posted"]]
        for move_line in get_model("account.move.line").search_browse(cond):
            move=move_line.move_id
            acc=move_line.account_id
            rec=move_line.reconcile_id
            if rec:
                amt=-rec.balance
            else:
                amt=move_line.credit-move_line.debit
            if amt==0:
                continue
            if cred.type=="out":
                amt=-amt
            line_vals={
                "move_line_id": move_line.id,
                "move_id": [move.id,move.name_get()[0][1]],
                "date": move.date,
                "account_id": [acc.id,acc.name_get()[0][1]],
                "amount_due": amt,
            }
            lines.append(line_vals)
        vals = {
            "credit_id": [cred.id, cred.name_get()[0][1]],
            "lines": lines,
            "type": cred.type,
            "amount_credit": cred.amount_credit_remain,
            "amount_alloc": 0,
            "amount_remain": cred.amount_credit_remain,
        }
        return vals

    def allocate(self, ids, context={}):
        obj = self.browse(ids)[0]
        cred=obj.credit_id
        if cred.inv_type != "credit":
            raise Exception("Wrong credit note type")
        contact=cred.contact_id
        for line in obj.lines:
            if not line.amount:
                continue
            inv_move_line=line.move_line_id
            inv=inv_move_line.move_id.related_id
            if inv._model!="account.invoice":
                inv=None
            desc = "Credit allocation: %s" % contact.name
            move_vals={
                "journal_id": inv_move_line.move_id.journal_id.id, # XXX
                "date": obj.date,
                "narration": desc,
                "lines": [],
                "related_id": "account.invoice,%d"%inv.id,
            }
            move_id = get_model("account.move").create(move_vals)
            if cred.type == "in":
                sign = -1
            else:
                sign = 1
            amt=line.amount*sign # TODO: currency convert
            line_vals={
                "move_id": move_id,
                "description": desc,
                "account_id": cred.account_id.id,
                "debit": amt > 0 and amt or 0,
                "credit": amt < 0 and -amt or 0,
                "contact_id": contact.id,
            }
            line1_id=get_model("account.move.line").create(line_vals)
            line_vals={
                "move_id": move_id,
                "description": desc,
                "account_id": inv_move_line.account_id.id,
                "debit": amt < 0 and -amt or 0,
                "credit": amt > 0 and amt or 0,
                "contact_id": contact.id,
            }
            line2_id=get_model("account.move.line").create(line_vals)
            get_model("account.move").post([move_id])
            if not cred.move_id or not cred.move_id.lines:
                raise Exception("Failed to find credit note journal entry line to reconcile")
            cred_line_id=cred.move_id.lines[0].id
            get_model("account.move.line").reconcile([cred_line_id,line1_id])
            get_model("account.move.line").reconcile([inv_move_line.id,line2_id])
        return {
            "next": {
                "name": "view_invoice",
                "active_id": obj.credit_id.id,
            },
            "flash": "Credit note updated.",
        }

    def onchange_amount(self, context={}):
        data = context["data"]
        amt = 0
        for line in data["lines"]:
            amt += line.get("amount", 0)
        data["amount_alloc"] = amt
        data["amount_remain"] = data["amount_credit"] - amt
        return data

AllocWizard.register()
