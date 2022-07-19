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


class AutoReconcile(Model):
    _name = "auto.reconcile"
    _transient = True
    _fields = {
        "account_id": fields.Many2One("account.account", "Account"),
        "contact_id": fields.Many2One("contact", "Contact"),
        "to_date": fields.Date("To Date"),
    }

    def do_reconcile(self, ids, context={}):
        obj = self.browse(ids)[0]
        account_id = obj.account_id.id
        cond = [["account_id", "=", account_id]]
        if obj.contact_id:
            cond.append(["contact_id", "=", obj.contact_id.id])
        if obj.to_date:
            cond.append(["move_date", "<=", obj.to_date])
        num_rec = 0
        unrec = {}
        for line in get_model("account.move.line").search_browse(cond, order="move_id.date,id"):
            if not line.contact_id:
                continue
            if line.reconcile_id and line.reconcile_id.balance < 0:  # TODO: speed
                continue
            amt = line.debit - line.credit
            key2 = "%d,%.2f" % (line.contact_id.id, -amt)
            line2_ids = unrec.get(key2)
            if line2_ids:
                line2_id = line2_ids.pop(0)
                if not line2_ids:
                    del unrec[key2]
                rec_id = get_model("account.reconcile").create({})
                get_model("account.move.line").write([line.id, line2_id], {"reconcile_id": rec_id})
                num_rec += 2
            else:
                key = "%d,%.2f" % (line.contact_id.id, amt)
                unrec.setdefault(key, []).append(line.id)
        return {
            "next": {
                "name": "account_reconcile",
            },
            "flash": "%d transactions reconciled" % num_rec,
        }

AutoReconcile.register()
