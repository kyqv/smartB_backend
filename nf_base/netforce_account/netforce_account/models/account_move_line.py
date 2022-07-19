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
from netforce import database


class MoveLine(Model):
    _name = "account.move.line"
    _name_field = "move_id"
    #_key = ["move_id", "sequence"]
    _fields = {
        "move_id": fields.Many2One("account.move", "Journal Entry", required=True, on_delete="cascade", search=True),
        "description": fields.Text("Description", required=True, search=True),
        "account_id": fields.Many2One("account.account", "Account", required=True, search=True),
        "debit": fields.Decimal("Debit", required=True),
        "credit": fields.Decimal("Credit", required=True),
        "statement_line_id": fields.Many2One("account.statement.line", "Statement Line"),  # XXX: not used any more
        # XXX: simplify this...
        "statement_line_search": fields.Many2One("account.statement.line", "Statement Line", store=False, function_search="_search_statement_line"),
        "state": fields.Selection([["not_reconciled", "Not Reconciled"], ["reconciled", "Reconciled"]], "Status"),
        # XXX: remove store?
        "move_date": fields.Date("Date", function="_get_related", function_context={"path": "move_id.date"}, store=True, search=True),
        "move_state": fields.Selection([["draft", "Draft"], ["posted", "Posted"], ["voided", "Voided"]], "Status", function="_get_related", function_context={"path": "move_id.state"}, store=True),
        "move_narration": fields.Char("Narration", function="_get_related", function_context={"path": "move_id.narration"}),
        "move_type": fields.Selection([["invoice", "Invoice"], ["payment", "Payment"], ["transfer", "Transfer"], ["picking", "Picking"], ["stock_count", "Stock Count"], ["claim", "Claim"], ["manual", "Manual"]], "Type", function="_get_related", function_context={"path": "move_id.type"}),
        "move_ref": fields.Char("Reference", function="_get_related", function_context={"path": "move_id.ref"}),
        "move_number": fields.Char("Number", function="_get_related", function_context={"path": "move_id.number"}, function_search="_search_related", search=True),
        "account_name": fields.Char("Account Name", function="_get_related", function_context={"path": "account_id.name"}),
        "account_code": fields.Char("Account Code", function="_get_related", function_context={"path": "account_id.code"}),
        "stock_move_id": fields.Many2One("stock.move", "Stock Move"),
        "product_id": fields.Many2One("product", "Product"),
        #"tax_comp_id": fields.Many2One("account.tax.component", "Tax Comp.", on_delete="restrict"),
        "tax_comp_id": fields.Many2One("account.tax.component", "Tax Comp."),
        "tax_base": fields.Decimal("Tax Base"),
        "contact_id": fields.Many2One("contact", "Contact", search=True),
        "due_date": fields.Date("Due Date"),
        "track_id": fields.Many2One("account.track.categ", "Track-1", condition=[["type", "=", "1"]]),
        "track2_id": fields.Many2One("account.track.categ", "Track-2", condition=[["type", "=", "2"]]),
        "invoice_id": fields.Many2One("account.invoice", "Invoice"),
        "qty": fields.Decimal("Qty"),
        "reconcile_id": fields.Many2One("account.reconcile", "Reconciliation"),
        "bank_reconcile_id": fields.Many2One("account.bank.reconcile", "Bank Reconciliation"), # XXX: deprecated
        "statement_lines": fields.Many2Many("account.statement.line", "Statement Lines"),
        "is_account_reconciled": fields.Boolean("Is Reconciled?", function="_is_account_reconciled"),
        "empty_contact": fields.Boolean("Empty Contact", store=False, function_search="_search_empty_contact", search=True),
        "tax_no": fields.Char("Tax No."),
        "tax_date": fields.Date("Tax Invoice Date"),
        "sequence": fields.Integer("Sequence"),
        "amount_cur": fields.Decimal("Currency Amt"),
    }

    _defaults = {
        "state": "not_reconciled",
        "debit": 0,
        "credit": 0,
    }
    _indexes = [
        ("account_id", "move_date"),
    ]
    _order = "sequence,id"

    def create(self,vals,**kw):
        if not vals.get("description"):
            move_id=vals["move_id"]
            move=get_model("account.move").browse(move_id)
            vals["description"]=move.narration
        new_id=super().create(vals,**kw)
        return new_id

    def view_transaction(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": obj.move_id.id,
            }
        }

    def unreconcile(self, ids, context={}):
        st_line_ids = []
        for obj in self.browse(ids):
            for st_line in obj.statement_lines:
                st_line_ids.append(st_line.id)
        st_line_ids = list(set(st_line_ids))
        get_model("account.statement.line").unreconcile(st_line_ids)
        self.write(ids, {"state": "not_reconciled"})

    def reconcile(self, ids, context={}):
        print("MoveLine.reconcile", ids)
        rec_id = get_model("account.reconcile").create({})
        all_ids = ids[:]
        for line in self.browse(ids):
            rec = line.reconcile_id
            if not rec:
                continue
            for rline in rec.lines:
                all_ids.append(rline.id)
        all_ids = list(set(all_ids))
        acc_id = None
        for obj in self.browse(all_ids):
            if not acc_id:
                acc_id = obj.account_id.id
            else:
                if obj.account_id.id != acc_id:
                    acc=get_model("account.account").browse(acc_id)
                    raise Exception("Can only reconcile transactions of same account (%s / %s)"%(obj.account_id.code,acc.code))
        self.write(all_ids, {"reconcile_id": rec_id})
        inv_ids=[]
        for obj in self.browse(all_ids):
            move=obj.move_id
            rel=move.related_id
            if rel._model=="account.invoice":
                inv_ids.append(rel.id)
        if inv_ids:
            get_model("account.invoice").function_store(inv_ids)

    def unreconcile_manual(self, ids, context={}):
        all_ids = ids[:]
        for line in self.browse(ids):
            rec = line.reconcile_id
            if not rec:
                continue
            for rline in rec.lines:
                all_ids.append(rline.id)
        all_ids = list(set(all_ids))
        self.write(all_ids,{"reconcile_id":None})

    def write(self, ids, vals, **kw):
        rec_ids = []
        for obj in self.browse(ids):
            if obj.reconcile_id:
                rec_ids.append(obj.reconcile_id.id)
        super().write(ids, vals, **kw)
        for obj in self.browse(ids):
            if obj.reconcile_id:
                rec_ids.append(obj.reconcile_id.id)
        if rec_ids:
            rec_ids = list(set(rec_ids))
            get_model("account.reconcile").function_store(rec_ids)

    def delete(self, ids, **kw):
        for obj in self.browse(ids):
            if obj.move_id.state=="posted":
                raise Exception("Can not delete line of posted journal entry")
        rec_ids = []
        for obj in self.browse(ids):
            if obj.reconcile_id:
                rec_ids.append(obj.reconcile_id.id)
        super().delete(ids, **kw)
        if rec_ids:
            rec_ids = list(set(rec_ids))
            get_model("account.reconcile").function_store(rec_ids)

    def _is_account_reconciled(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.reconcile_id:
                vals[obj.id] = abs(obj.reconcile_id.balance) == 0
            else:
                vals[obj.id] = False
        return vals

    def _search_empty_contact(self, clause, context={}):
        if clause[2]:
            return [["contact_id", "=", None]]
        else:
            return [["contact_id", "!=", None]]

    def reconcile_remove_from_all(self, ids, context={}):
        print("reconcile_remove_from_all", ids)
        self.write(ids, {"statement_lines": [("set", [])]})

MoveLine.register()
