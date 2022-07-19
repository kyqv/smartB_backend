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
from netforce.access import get_active_company


class Transfer(Model):
    _name = "account.transfer"
    _string = "Transfer"
    _name_field = "date"
    _multi_company = True
    _fields = {
        "date": fields.Date("Date", required=True, search=True),
        "account_from_id": fields.Many2One("account.account", "From Account", required=True, condition=[["type", "!=", "view"]], search=True),
        "account_to_id": fields.Many2One("account.account", "To Account", required=True, condition=[["type", "!=", "view"]], search=True),
        "amount": fields.Decimal("Paid Amount", required=True),
        "amount_received": fields.Decimal("Received Amount", required=True),
        "move_id": fields.Many2One("account.move", "Journal Entry"),
        "ref": fields.Char("Reference", search=True),
        "track_id": fields.Many2One("account.track.categ", "Track-1", condition=[["type", "=", "1"]]),
        "track2_id": fields.Many2One("account.track.categ", "Track-2", condition=[["type", "=", "2"]]),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "state": fields.Selection([["draft", "Draft"], ["posted", "Posted"], ["voided", "Voided"]], "State"),
        "number": fields.Char("Number", required=True, search=True),
        "company_id": fields.Many2One("company", "Company"),
        "documents": fields.One2Many("document", "related_id", "Documents"),
    }
    _order = "date desc,id desc"

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="transfer")
        if not seq_id:
            return
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "state": "draft",
        "number": _get_number,
        "company_id": lambda *a: get_active_company(),
    }

    def create(self, vals, context={}):
        new_id = super(Transfer, self).create(vals)
        return new_id

    def do_transfer(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.post()
        return {
            "next": {
                "name": "bank_list",
            },
            "flash": "Transfer recorded successfully",
        }

    def post(self, ids, context={}):
        settings = get_model("settings").browse(1)
        for obj in self.browse(ids):
            desc = "Transfer"
            if obj.ref:
                desc += " " + obj.ref
            journal_id = settings.general_journal_id.id
            if not journal_id:
                raise Exception("General journal not found")
            amt = get_model("currency").convert(obj.amount, obj.account_from_id.currency_id.id, settings.currency_id.id)
            move_vals = {
                "journal_id": journal_id,
                "number": obj.number,
                "date": obj.date,
                "narration": desc,
                "related_id": "account.transfer,%s" % obj.id,
                "company_id": obj.company_id.id,
                "lines": [],
            }
            line_vals = {
                "description": desc,
                "account_id": obj.account_to_id.id,
                "debit": amt,
                "credit": 0,
                "track_id": obj.track_id.id,
            }
            if obj.account_to_id.currency_id.id != settings.currency_id.id:
                line_vals["amount_cur"] = obj.amount_received
            move_vals["lines"].append(("create", line_vals))
            line_vals = {
                "description": desc,
                "account_id": obj.account_from_id.id,
                "debit": 0,
                "credit": amt,
                "track_id": obj.track_id.id,
            }
            if obj.account_from_id.currency_id.id != settings.currency_id.id:
                line_vals["amount_cur"] = -obj.amount
            move_vals["lines"].append(("create", line_vals))
            move_id = get_model("account.move").create(move_vals)
            move_vals["lines"].append(("create", line_vals))
            get_model("account.move").post([move_id])
            obj.write({"move_id": move_id, "state": "posted"})

    def to_draft(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.move_id:
                obj.move_id.void()
                obj.move_id.delete()
            obj.write({"state": "draft"})

    def void(self, ids, context={}):
        for obj in self.browse(ids):
            if obj.move_id:
                obj.move_id.void()
            obj.write({"state": "voided"})

    def copy(self, ids, context={}):
        obj = self.browse(ids)[0]
        vals = {
            "date": obj.date,
            "account_from_id": obj.account_from_id.id,
            "account_to_id": obj.account_to_id.id,
            "amount": obj.amount,
            "ref": obj.ref,
            "track_id": obj.track_id.id,
        }
        new_id = self.create(vals)
        return {
            "next": {
                "name": "bank_transfer",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "New transfer %d copied from %d" % (new_id, obj.id),
        }

    def view_journal_entry(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": obj.move_id.id,
            }
        }

    def onchange_date(self, context={}):
        data = context["data"]
        date = data["date"]
        number = self._get_number(context={"date": date})
        data["number"] = number
        return data

    def onchange_amount(self, context={}):
        data = context["data"]
        acc_from_id = data["account_from_id"]
        acc_from = get_model("account.account").browse(acc_from_id)
        acc_to_id = data["account_to_id"]
        acc_to = get_model("account.account").browse(acc_to_id)
        if not data["amount_received"]:
            data["amount_received"] = get_model("currency").convert(
                data["amount"], acc_from.currency_id.id, acc_to.currency_id.id)
        return data

    def onchange_amount_received(self, context={}):
        data = context["data"]
        acc_from_id = data["account_from_id"]
        acc_from = get_model("account.account").browse(acc_from_id)
        acc_to_id = data["account_to_id"]
        acc_to = get_model("account.account").browse(acc_to_id)
        if not data["amount"]:
            data["amount"] = get_model("currency").convert(
                data["amount_received"], acc_to.currency_id.id, acc_from.currency_id.id)
        return data

Transfer.register()
