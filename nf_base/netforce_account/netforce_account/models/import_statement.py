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
import csv
from io import StringIO
from netforce.database import get_active_db
import os
from datetime import *
from dateutil.relativedelta import *
from netforce import utils
from decimal import *


class ImportStatement(Model):
    _name = "import.statement"
    _transient = True
    _fields = {
        "account_id": fields.Many2One("account.account", "Account", required=True, on_delete="cascade"),
        "date_start": fields.Date("From Date", required=True),
        "date_end": fields.Date("To Date", required=True),
        "file": fields.File("CSV File", required=True),
        "encoding": fields.Selection([["utf-8", "UTF-8"], ["tis-620", "TIS-620"]], "Encoding", required=True),
    }
    _defaults = {
        "encoding": "utf-8",
    }

    def import_data(self, ids, context={}):
        obj = self.browse(ids[0])
        acc_id = obj.account_id.id
        dbname = get_active_db()
        if not obj.file:
            raise Exception("Missing file")
        path=utils.get_file_path(obj.file)
        data = open(path, "rb").read().decode(obj.encoding)
        found_delim = False
        for delim in (",", ";", "\t"):
            try:
                try:
                    rd = csv.reader(StringIO(data), delimiter=delim)
                except:
                    raise Exception("Invalid CSV file")
                headers = next(rd)
                headers = [h.strip() for h in headers]
                for h in ["Date", "Description", "Spent", "Received", "Balance"]:
                    if not h in headers:
                        raise Exception("Missing header: '%s'" % h)
                found_delim = True
                break
            except:
                pass
        if not found_delim:
            raise Exception("Failed to open CSV file")
        rows = [r for r in rd]
        if not rows:
            raise Exception("Statement is empty")
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d/%m/%y", "%m/%d/%y", "%d-%m-%y", "%m-%d-%y"]
        date_fmt = None
        for fmt in formats:
            fmt_ok = True
            for row in rows:
                vals = dict(zip(headers, row))
                date = vals["Date"].strip()
                if not date:
                    continue
                try:
                    datetime.strptime(date, fmt)
                except:
                    fmt_ok = False
                    break
            if fmt_ok:
                date_fmt = fmt
                break
        if not date_fmt:
            raise Exception("Could not detect date format")
        lines = []
        for i, row in enumerate(rows):
            vals = dict(zip(headers, row))
            try:
                date = vals["Date"].strip()
                if not date:
                    raise Exception("Missing date")
                date = datetime.strptime(date, date_fmt).strftime("%Y-%m-%d")
                if date < obj.date_start:
                    raise Exception("Transaction date is before start date: %s" % date)
                if date > obj.date_end:
                    raise Exception("Transaction date is after end date: %s" % date)
                balance = vals["Balance"].strip().replace(",", "")
                if not balance:
                    raise Exception("missing balance")
                try:
                    balance = Decimal(balance)
                except:
                    raise Exception("Failed to read Balance amount")
                description = vals.get("Description").strip()
                try:
                    spent = vals["Spent"].strip().replace(",", "")
                    spent = Decimal(spent) if spent else 0
                except:
                    raise Exception("Failed to read Spent amount")
                try:
                    received = vals["Received"].strip().replace(",", "")
                    received = Decimal(received) if received else 0
                except:
                    raise Exception("Failed to read Received amount")
                if not spent and not received:
                    raise Exception("No spent or received amount")
                if spent and received:
                    raise Exception("Can not have both Spent and Received amounts on the same line")
                line_vals = {
                    "date": date,
                    "balance": balance,
                    "description": description,
                    "spent": spent,
                    "received": received,
                }
                lines.append(line_vals)
            except Exception as e:
                raise Exception("Error on line %d (%s)" % (i + 2, e))
        if not lines:
            raise Exception("Empty statement")
        first_bal = lines[0]["balance"] + lines[0]["spent"] - lines[0]["received"]
        first_date = lines[0]["date"]
        res = get_model("account.statement.line").search(
            [["statement_id.account_id", "=", acc_id], ["date", "<", first_date]], order="date desc,id desc", limit=1)
        if res:
            prev_line = get_model("account.statement.line").browse(res[0])
            prev_bal = prev_line.balance
            if abs(first_bal-prev_bal)>0.001:
                raise Exception("Invalid balance: previous balance is %.2f" % prev_bal)
        st_vals = {
            "account_id": acc_id,
            "date_start": obj.date_start,
            "date_end": obj.date_end,
            "balance_start": first_bal,
            "lines": [("create", v) for v in lines],
        }
        stmt_id = get_model("account.statement").create(st_vals)
        return {
            "next": {
                "name": "statement",
                "mode": "page",
                "active_id": stmt_id,
            }
        }

    def onchange_account(self, context={}):
        data = context["data"]
        account_id = data["account_id"]
        acc = get_model("account.account").browse(account_id)
        if acc.statements:
            st = acc.statements[0]
            d = datetime.strptime(st.date_end, "%Y-%m-%d") + timedelta(days=1)
            data["date_start"] = d.strftime("%Y-%m-%d")
            data["date_end"] = (d + relativedelta(day=31)).strftime("%Y-%m-%d")
        else:
            data["date_start"] = (datetime.today() - relativedelta(day=1)).strftime("%Y-%m-%d")
            data["date_end"] = (datetime.today() + relativedelta(day=31)).strftime("%Y-%m-%d")
        return data

ImportStatement.register()
