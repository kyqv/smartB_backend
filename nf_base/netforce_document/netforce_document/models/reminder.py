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


class Reminder(Model):
    _name = "reminder"
    _string = "Reminder"
    _fields = {
        "scheduled_date": fields.Date("Scheduled Date", required=True),
        "doc_id": fields.Many2One("document", "Document", required=True, on_delete="cascade"),
        "user_id": fields.Many2One("base.user", "To User", required=True),
        "subject": fields.Char("Subject", required=True),
        "body": fields.Text("Body"),
        "state": fields.Selection([["pending", "Pending"], ["sent", "Sent"]], "Status", required=True),
    }
    _order = "scheduled_date,id"

    _defaults = {
        "scheduled_date": lambda *a: time.strftime("%Y-%m-%d"),
        "state": "pending",
    }

    def send_email(self, ids, context={}):
        for obj in self.browse(ids):
            to_addr = obj.user_id.email
            if not to_addr:
                continue
            vals = {
                "state": "to_send",
                "from_addr": "support@netforce.com",
                "to_addrs": to_addr,
                "subject": obj.subject,
                "body": obj.body,
            }
            get_model("email.message").create(vals)
            obj.write({"state": "sent"})

    def send_reminders(self):
        t = time.strftime("%Y-%m-%d")
        ids = self.search([["scheduled_date", "<=", t], ["state", "=", "pending"]])
        self.send_email(ids)

Reminder.register()
