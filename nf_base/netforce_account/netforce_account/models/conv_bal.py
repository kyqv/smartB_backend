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
from netforce.action import get_action
import time
from netforce.utils import get_file_path
from io import StringIO
import csv
import datetime
from netforce import tasks


class ConvBal(Model):
    _name = "conv.bal"
    _transient = True
    _fields = {
        "date": fields.Date("Conversion Date", required=True),
        "accounts": fields.One2Many("conv.account", "conv_id", "Account Balances"),
        "sale_invoices": fields.One2Many("conv.sale.invoice", "conv_id", "Sales Invoices"),
        "purch_invoices": fields.One2Many("conv.purch.invoice", "conv_id", "Purchase Invoices"),
        "total_debit": fields.Decimal("Total Debit", function="get_total", function_multi=True),
        "total_credit": fields.Decimal("Total Credit", function="get_total", function_multi=True),
        "total_sale": fields.Decimal("Total Amount Due", function="get_total", function_multi=True),
        "total_purch": fields.Decimal("Total Amount Due", function="get_total", function_multi=True),
        "total_ar": fields.Decimal("Account Receivable Balance", function="get_total", function_multi=True),
        "total_ap": fields.Decimal("Account Payable Balance", function="get_total", function_multi=True),
        "move_id": fields.Many2One("account.move", "Opening Entry"),
        "file": fields.File("CSV File"),
        "date_fmt": fields.Char("Date Format"),
    }
    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-01"),
        "date_fmt": "%m/%d/%Y",
    }

    def get_total(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            total_debit = 0
            total_credit = 0
            total_sale = 0
            total_purch = 0
            total_ar = 0
            total_ap = 0
            for acc in obj.accounts:
                total_debit += acc.debit or 0
                total_credit += acc.credit or 0
                if acc.account_id.type == "receivable":
                    total_ar += (acc.debit or 0) - (acc.credit or 0)
                if acc.account_id.type == "payable":
                    total_ap += (acc.credit or 0) - (acc.debit or 0)
            for inv in obj.sale_invoices:
                total_sale += inv.amount_due
            for inv in obj.purch_invoices:
                total_purch += inv.amount_due
            vals[obj.id] = {
                "total_debit": total_debit,
                "total_credit": total_credit,
                "total_sale": total_sale,
                "total_purch": total_purch,
                "total_ar": total_ar,
                "total_ap": total_ap,
            }
        return vals

    def next1(self, ids, context={}):
        obj = self.browse(ids)[0]
        if obj.total_debit - obj.total_credit != 0:
            raise Exception("Conversion balance is not balanced")
        return {
            "next": {
                "name": "conv_bal",
                "active_id": obj.id,
                "view_xml": "conv_bal2",
            }
        }

    def next2(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "conv_bal",
                "active_id": obj.id,
                "view_xml": "conv_bal3",
            }
        }

    def back2(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "conv_bal",
                "active_id": obj.id,
                "view_xml": "conv_bal1",
            }
        }

    def next3(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.create_open_entry(context=context)
        obj.create_sale_invoices(context=context)
        obj.create_purch_invoices(context=context)
        return {
            "next": {
                "name": "journal_entry",
                "mode": "form",
                "active_id": obj.move_id.id,
            },
            "flash": "Conversion balance created successfully",
        }

    def back3(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "conv_bal",
                "active_id": obj.id,
                "view_xml": "conv_bal2",
            }
        }

    def create_open_entry(self, ids, context={}):
        obj = self.browse(ids)[0]
        job_id=context.get("job_id")
        if job_id:
            if tasks.is_aborted(job_id):
                return
            tasks.set_progress(job_id,1,"Creating opening journal entry")
        settings = get_model("settings").browse(1)
        desc = "Conversion balance %s" % obj.date
        if not settings.general_journal_id:
            raise Exception("General journal not found")
        journal_id = settings.general_journal_id.id
        vals = {
            "journal_id": journal_id,
            "number": "OPENING ENTRY",
            "date": obj.date,
            "narration": desc,
        }
        move_id = get_model("account.move").create(vals)
        for acc in obj.accounts:
            if acc.account_id.type in ("receivable", "payable"):
                continue
            line_vals = {
                "move_id": move_id,
                "description": desc,
                "account_id": acc.account_id.id,
                "debit": acc.debit or 0,
                "credit": acc.credit or 0,
                "amount_cur": acc.amount_cur,
            }
            line_id = get_model("account.move.line").create(line_vals)
        for inv in obj.sale_invoices:
            amt = inv.amount_due
            line_vals = {
                "move_id": move_id,
                "description": desc + ", %s" % inv.number,
                "account_id": inv.account_id.id,
                "debit": amt > 0 and amt or 0,
                "credit": amt < 0 and -amt or 0,
                "contact_id": inv.contact_id.id,
                "amount_cur": inv.amount_cur,
            }
            line_id = get_model("account.move.line").create(line_vals)
            inv.write({"move_line_id": line_id})
        for inv in obj.purch_invoices:
            amt = -inv.amount_due
            line_vals = {
                "move_id": move_id,
                "description": desc + ", %s" % inv.number,
                "account_id": inv.account_id.id,
                "debit": amt > 0 and amt or 0,
                "credit": amt < 0 and -amt or 0,
                "contact_id": inv.contact_id.id,
                "amount_cur": -inv.amount_cur if inv.amount_cur is not None else None,
            }
            line_id = get_model("account.move.line").create(line_vals)
            inv.write({"move_line_id": line_id})
        get_model("account.move").post([move_id])
        obj.write({"move_id": move_id})

    def create_sale_invoices(self, ids, context={}):
        obj = self.browse(ids)[0]
        job_id=context.get("job_id")
        settings = get_model("settings").browse(1)
        desc = "Conversion balance %s" % obj.date
        invs=list(obj.sale_invoices)
        for i,inv in enumerate(invs):
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*100/len(invs),"Creating customer invoice %s/%s"%(i+1,len(invs)))
            vals = {
                "type": "out",
                "inv_type": inv.amount_due >= 0 and "invoice" or "credit",
                "contact_id": inv.contact_id.id,
                "date": inv.date,
                "due_date": inv.due_date,
                "number": inv.number,
                "ref": inv.ref,
                "memo": desc,
                "lines": [],
                "state": "waiting_payment",
                "account_id": inv.account_id.id,
                "reconcile_move_line_id": inv.move_line_id.id,
                "currency_id": inv.account_id.currency_id.id,
                "currency_rate": inv.amount_due / inv.amount_cur if inv.amount_cur else None,
            }
            line_vals = {
                "description": desc,
                "amount": abs(inv.amount_cur or inv.amount_due),
            }
            vals["lines"].append(("create", line_vals))
            res = get_model("account.invoice").search([["number", "=", inv.number]])
            if res:
                inv2_id = res[0]
                inv2 = get_model("account.invoice").browse(inv2_id)
                if abs(inv2.amount_total) - abs(inv.amount_due) != 0:  # XXX
                    raise Exception("Failed to update invoice %s: different amount" % inv.number)
                if inv2.state == "draft":
                    raise Exception("Failed to update invoice %s: invalid state" % inv.number)
                inv2.write({
                    "move_id": obj.move_id.id,
                    "reconcile_move_line_id": inv.move_line_id.id,
                })
            else:
                get_model("account.invoice").create(vals)

    def create_purch_invoices(self, ids, context={}):
        obj = self.browse(ids)[0]
        settings = get_model("settings").browse(1)
        desc = "Conversion balance %s" % obj.date
        job_id=context.get("job_id")
        invs=list(obj.purch_invoices)
        for i,inv in enumerate(invs):
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i*100/len(invs),"Creating supplier invoice %s/%s"%(i+1,len(invs)))
            vals = {
                "type": "in",
                "inv_type": inv.amount_due >= 0 and "invoice" or "credit",
                "contact_id": inv.contact_id.id,
                "date": inv.date,
                "due_date": inv.due_date,
                "number": inv.number,
                "ref": inv.ref,
                "memo": desc,
                "lines": [],
                "state": "waiting_payment",
                "account_id": inv.account_id.id,
                "reconcile_move_line_id": inv.move_line_id.id,
                "currency_id": inv.account_id.currency_id.id,
                "currency_rate": inv.amount_due / inv.amount_cur if inv.amount_cur else None,
            }
            line_vals = {
                "description": desc,
                "amount": abs(inv.amount_cur or inv.amount_due),
            }
            vals["lines"].append(("create", line_vals))
            res = get_model("account.invoice").search([["number", "=", inv.number]])
            if res:
                inv2_id = res[0]
                inv2 = get_model("account.invoice").browse(inv2_id)
                if abs(inv2.amount_total) - abs(inv.amount_due) != 0:  # XXX
                    raise Exception("Failed to update invoice %s" % inv.number)
                if inv2.state == "draft":
                    raise Exception("Failed to update invoice %s: invalid state" % inv.number)
                inv2.write({
                    "move_id": obj.move_id.id,
                    "reconcile_move_line_id": inv.move_line_id.id,
                })
            else:
                get_model("account.invoice").create(vals)

    def update_total(self, context):
        data = context["data"]
        data["total_debit"] = 0
        data["total_credit"] = 0
        for line in data["accounts"]:
            if not line:
                continue
            debit = line.get("debit") or 0
            credit = line.get("credit") or 0
            data["total_debit"] += debit
            data["total_credit"] += credit
        return data

    def import_acc(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"file": None})
        return {
            "next": {
                "view": "form_popup",
                "model": "conv.bal",
                "active_id": obj.id,
                "target": "popup",
                "view_xml": "conv_import1",
            }
        }

    def import_sale(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"file": None})
        return {
            "next": {
                "view": "form_popup",
                "model": "conv.bal",
                "active_id": obj.id,
                "target": "popup",
                "view_xml": "conv_import2",
            }
        }

    def import_purch(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.write({"file": None})
        return {
            "next": {
                "view": "form_popup",
                "model": "conv.bal",
                "active_id": obj.id,
                "target": "popup",
                "view_xml": "conv_import3",
            }
        }

    def import_acc_file(self, ids, context):
        print("import_acc_file",ids)
        obj = self.browse(ids)[0]
        path = get_file_path(obj.file)
        data = open(path).read()
        rd = csv.reader(StringIO(data))
        headers = next(rd)
        headers = [h.strip() for h in headers]
        del_ids = get_model("conv.account").search([["conv_id", "=", obj.id]])
        get_model("conv.account").delete(del_ids)
        for row in rd:
            print("row", row)
            line = dict(zip(headers, row))
            print("line", line)
            if not line.get("Account"):
                continue
            acc_code = line["Account"].strip()
            if not acc_code:
                continue
            res = get_model("account.account").search([["code", "=", acc_code]])
            if not res:
                raise Exception("Account code not found: %s" % acc_code)
            acc_id = res[0]
            debit = float(line["Debit"].strip().replace(",", "") or 0)
            credit = float(line["Credit"].strip().replace(",", "") or 0)
            amount_cur = line["Currency Amt"].strip().replace(",", "")
            if amount_cur:
                amount_cur = float(amount_cur)
            else:
                amount_cur = None
            vals = {
                "conv_id": obj.id,
                "account_id": acc_id,
                "debit": debit,
                "credit": credit,
                "amount_cur": amount_cur,
            }
            get_model("conv.account").create(vals)
        return {
            "next": {
                "name": "conv_bal",
                "active_id": obj.id,
                "view_xml": "conv_bal1",
            }
        }

    def import_sale_file(self, ids, context):
        obj = self.browse(ids)[0]
        path = get_file_path(obj.file)
        data = open(path).read()
        rd = csv.reader(StringIO(data))
        headers = next(rd)
        headers = [h.strip() for h in headers]
        del_ids = get_model("conv.sale.invoice").search([["conv_id", "=", obj.id]])
        get_model("conv.sale.invoice").delete(del_ids)
        i = 1
        for row in rd:
            i += 1
            try:
                print("row", row)
                line = dict(zip(headers, row))
                print("line", line)
                if not line.get("Number"):
                    continue
                number = line["Number"].strip()
                if not number:
                    continue
                ref = line["Reference"].strip()
                contact_name = line["Contact"].strip()
                res = get_model("contact").search([["name", "=", contact_name]])
                if not res:
                    res = get_model("contact").search([["code", "=", contact_name]])
                    if not res:
                        raise Exception("Contact not found: '%s'" % contact_name)
                contact_id = res[0]
                date = datetime.datetime.strptime(line["Date"].strip(), obj.date_fmt).strftime("%Y-%m-%d")
                due_date = datetime.datetime.strptime(line["Due Date"].strip(), obj.date_fmt).strftime("%Y-%m-%d")
                amount_due = float(line["Amount Due"].strip().replace(",", "") or 0)
                acc_code = line["Account"].strip()
                if not acc_code:
                    raise Exception("Account is missing")
                res = get_model("account.account").search([["code", "=", acc_code]])
                if not res:
                    raise Exception("Account code not found: %s" % acc_code)
                acc_id = res[0]
                amount_cur = line["Amount Cur"].strip().replace(",", "")
                if amount_cur:
                    amount_cur = float(amount_cur)
                else:
                    amount_cur = None
                vals = {
                    "conv_id": obj.id,
                    "number": number,
                    "ref": ref,
                    "contact_id": contact_id,
                    "date": date,
                    "due_date": due_date,
                    "amount_due": amount_due,
                    "account_id": acc_id,
                    "amount_cur": amount_cur,
                }
                get_model("conv.sale.invoice").create(vals)
            except Exception as e:
                raise Exception("Error line %d: %s" % (i, e))
        return {
            "next": {
                "name": "conv_bal",
                "active_id": obj.id,
                "view_xml": "conv_bal2",
            }
        }

    def import_purch_file(self, ids, context):
        obj = self.browse(ids)[0]
        path = get_file_path(obj.file)
        data = open(path).read()
        rd = csv.reader(StringIO(data))
        headers = next(rd)
        headers = [h.strip() for h in headers]
        del_ids = get_model("conv.purch.invoice").search([["conv_id", "=", obj.id]])
        get_model("conv.purch.invoice").delete(del_ids)
        i = 1
        for row in rd:
            i += 1
            try:
                print("row", row)
                line = dict(zip(headers, row))
                print("line", line)
                if not line.get("Number"):
                    continue
                number = line["Number"].strip()
                if not number:
                    continue
                ref = line["Reference"].strip()
                contact_name = line["Contact"].strip()
                res = get_model("contact").search([["name", "=", contact_name]])
                if not res:
                    res = get_model("contact").search([["code", "=", contact_name]])
                    if not res:
                        raise Exception("Contact not found: '%s'" % contact_name)
                contact_id = res[0]
                date = datetime.datetime.strptime(line["Date"].strip(), obj.date_fmt).strftime("%Y-%m-%d")
                due_date = datetime.datetime.strptime(line["Due Date"].strip(), obj.date_fmt).strftime("%Y-%m-%d")
                amount_due = float(line["Amount Due"].strip().replace(",", "") or 0)
                acc_code = line["Account"].strip()
                if not acc_code:
                    raise Exception("Account is missing")
                res = get_model("account.account").search([["code", "=", acc_code]])
                if not res:
                    raise Exception("Account code not found: %s" % acc_code)
                acc_id = res[0]
                amount_cur = line["Amount Cur"].strip().replace(",", "")
                if amount_cur:
                    amount_cur = float(amount_cur)
                else:
                    amount_cur = None
                vals = {
                    "conv_id": obj.id,
                    "number": number,
                    "ref": ref,
                    "contact_id": contact_id,
                    "date": date,
                    "due_date": due_date,
                    "amount_due": amount_due,
                    "account_id": acc_id,
                    "amount_cur": amount_cur,
                }
                get_model("conv.purch.invoice").create(vals)
            except Exception as e:
                raise Exception("Error line %d: %s" % (i, e))
        return {
            "next": {
                "name": "conv_bal",
                "active_id": obj.id,
                "view_xml": "conv_bal3",
            }
        }

ConvBal.register()
