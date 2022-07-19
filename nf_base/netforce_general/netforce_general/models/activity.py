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
import smtplib
import poplib
import email
from email.utils import parseaddr, parsedate
from email.header import decode_header
from netforce import database
import datetime


def conv_charset(charset):
    if charset == "windows-874":
        charset = "cp874"
    return charset


class Activity(Model):
    _name = "activity"
    _string = "Activity"
    _name_field = "subject"
    _fields = {
        "type": fields.Selection([["task", "Task"], ["event", "Event"], ["meeting", "Meeting"], ["call", "Call"]], "Activity Type", required=True, search=True),
        "user_id": fields.Many2One("base.user", "Assigned To", search=True, required=True),
        "subject": fields.Char("Subject", required=True, size=128, search=True),
        "date": fields.Date("Date", search=True),
        "due_date": fields.Date("Due Date"),
        "description": fields.Text("Description"),
        "body": fields.Text("Body"),
        "state": fields.Selection([["new", "Not Started"], ["in_progress", "In Progress"], ["done", "Completed"], ["waiting", "Waiting on someone else"], ["deferred", "Deferred"]], "Status", required=True),
        "priority": fields.Selection([["high", "High"], ["normal", "Normal"], ["low", "Low"]], "Priority"),
        "phone": fields.Char("Phone"),
        "email": fields.Char("Email"),
        "event_start": fields.DateTime("Start"),
        "event_end": fields.DateTime("End"),
        "location": fields.Char("Location"),
        "email_uid": fields.Char("Email UID"),
        "email_account_id": fields.Many2One("email.account", "Email Account"),
        "work_times": fields.One2Many("work.time", "activity_id", "Work Time"),
        "related_id": fields.Reference([["contact", "Contact"], ["sale.opportunity", "Opportunity"], ["sale.quot", "Quotation"], ["sale.order", "Sales Order"], ["job","Service Order"], ["issue", "Issue"]], "Related To"),
        "name_id": fields.Reference([["contact", "Contact"], ["sale.lead", "Lead"]], "Name"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "overdue": fields.Boolean("Overdue", function="get_overdue", function_search="search_overdue"),
    }

    def _get_name_id(self, context={}):
        defaults = context.get("defaults")
        if not defaults:
            return
        related = defaults.get("related_id")
        if not related:
            return
        model, model_id = related.split(",")
        model_id = int(model_id)
        if model == "sale.quot":
            obj = get_model("sale.quot").browse(model_id)
            return "contact,%s" % obj.contact_id.id

    _defaults = {
        "state": "new",
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "type": lambda self, ctx: ctx.get("activ_type") or "task",
        "name_id": _get_name_id,
    }
    _order = "due_date desc,date desc,id desc"

    # XXX
    def view_activity(self, ids, context={}):
        obj = self.browse(ids[0])
        return {
            "next": {
                "name": "activ",
                "mode": "form",
                "active_id": obj.id,
            }
        }

    def send_email(self, ids, context={}):
        obj = self.browse(ids)[0]
        from_addr = obj.user_id.email
        to_addr = obj.name_id.email
        if not to_addr:
            raise Exception("Email not found")
        res = get_model("email.account").search([["type", "=", "smtp"]])
        if not res:
            raise Exception("Email account not found")
        acc_id = res[0]
        acc = get_model("email.account").browse(acc_id)
        server = smtplib.SMTP(acc.host, acc.port)
        if acc.user:
            server.login(acc.user, acc.password)
        msg = "From: " + from_addr + "\r\n"
        msg += "To: " + to_addr + "\r\n"
        msg += "Subject: " + obj.subject + "\r\n\r\n"
        msg += obj.body
        server.sendmail(from_addr, [to_addr], msg)
        obj.write({"state": "done"})
        server.quit()

    # XXX: move this
    def fetch_email(self, context={}):
        print("fetch_email")
        acc_ids = get_model("email.account").search([["type", "=", "pop3"]])
        for acc in get_model("email.account").browse(acc_ids):
            print("connecting %s %s %s" % (acc.host, acc.port, acc.user))
            if acc.security == "ssl":
                serv = poplib.POP3_SSL(acc.host, acc.port)
            else:
                serv = poplib.POP3(acc.host, acc.port)
            serv.user(acc.user)
            if acc.password:
                serv.pass_(acc.password)
            try:
                resp, msg_list, size = serv.uidl()
                print("%d messages" % len(msg_list))
                for msg_info in msg_list:
                    msg_no, msg_uid = msg_info.decode().split()
                    print("msg_no", msg_no)
                    print("msg_uid", msg_uid)
                    try:
                        res = self.search_read([["email_account_id", "=", acc.id], ["email_uid", "=", msg_uid]])
                        if res:
                            print("skipping %s" % msg_uid)
                            serv.dele(msg_no)
                            continue
                        print("reading %s" % msg_uid)
                        resp, lines, size = serv.retr(msg_no)
                        msg = email.message_from_bytes(b"\n".join(lines))

                        def dec_header(data):
                            dh = decode_header(data or "")
                            s = ""
                            for data, charset in dh:
                                if isinstance(data, str):
                                    s += data
                                else:
                                    s += data.decode(conv_charset(charset) or "utf-8")
                            return s

                        def dec_date(data):
                            res = parsedate(data or "")
                            if not res:
                                return ""
                            return time.strftime("%Y-%m-%d %H:%M:%S", res)

                        def get_body(m):
                            if m.get_filename():
                                return "[Attachment: %s (%s)]\n" % (dec_header(m.get_filename()), m.get_content_type())
                            else:
                                if not m.is_multipart():
                                    charset = conv_charset(m.get_content_charset())
                                    return m.get_payload(decode=True).decode(charset or "utf-8", errors="replace")
                                else:
                                    data = m.get_payload()
                                    found = False
                                    res = []
                                    for m in data:
                                        fn = m.get_filename()
                                        if not fn:
                                            if found:
                                                continue
                                            found = True
                                        res.append(get_body(m))
                                    return "\n".join(res)
                        email_vals = {
                            "account_id": acc.id,
                            "msg_uid": msg_uid,
                            "date": dec_date(msg["Date"]),
                            "from_addr": parseaddr(msg["From"])[1][:64],
                            "to_addr": parseaddr(msg["To"])[1][:64],
                            "subject": dec_header(msg["Subject"])[:128],
                            "body": get_body(msg),
                        }
                        get_model("activity").import_email(email_vals)
                    except Exception as e:
                        print("WARNING: failed to import email %s", msg_uid)
                    finally:
                        serv.dele(msg_no)
            finally:
                print("quitting")
                db = database.get_connection()
                db.commit()
                serv.quit()

    # XXX: move this
    def import_email(self, email):
        print("import_email")
        print("from=%s to=%s subject=%s" % (email["from_addr"], email["to_addr"], email["subject"]))
        from_user_id = None
        from_contact_id = None
        from_lead_id = None
        to_user_id = None
        to_contact_id = None
        to_lead_id = None
        user_id = None
        contact_id = None
        lead_id = None
        contact_id = None
        opport_id = None
        quot_id = None
        sale_id = None
        name_id = None
        related_id = None
        res = get_model("base.user").search([["email", "=ilike", email["from_addr"]]])
        if res:
            from_user_id = res[0]
        res = get_model("contact").search([["email", "=ilike", email["from_addr"]]])
        if res:
            from_contact_id = res[0]
        else:
            res = get_model("sale.lead").search([["email", "=ilike", email["from_addr"]]])
            if res:
                from_lead_id = res[0]
        if not from_user_id and not from_contact_id and not from_lead_id:
            print("  => skipping (from)")
            return
        res = get_model("base.user").search([["email", "=ilike", email["to_addr"]]])
        if res:
            to_user_id = res[0]
        res = get_model("contact").search([["email", "=ilike", email["to_addr"]]])
        if res:
            to_contact_id = res[0]
        else:
            res = get_model("sale.lead").search([["email", "=ilike", email["to_addr"]]])
            if res:
                to_lead_id = res[0]
        if (from_contact_id or from_lead_id) and to_user_id:
            if from_contact_id:
                contact_id = from_contact_id
            if from_lead_id:
                lead_id = from_lead_id
            user_id = to_user_id
        elif from_user_id and (to_contact_id or to_lead_id):
            user_id = from_user_id
            if to_contact_id:
                contact_id = to_contact_id
            if to_lead_id:
                lead_id = to_lead_id
        else:
            print("  => skipping (from/to)")
            return
        if contact_id:
            contact = get_model("contact").browse(contact_id)
            if contact.contact_id:
                contact_id = contact.contact_id.id
        if contact_id and email["subject"]:
            subj = email["subject"].lower()
            opp_ids = get_model("sale.opportunity").search([["contact_id", "=", contact_id], ["state", "=", "open"]])
            for opp in get_model("sale.opportunity").browse(opp_ids):
                if subj.find(opp.name.lower()) != -1:
                    opport_id = opp.id
                    break
            quot_ids = get_model("sale.quot").search([["contact_id", "=", contact_id], ["state", "=", "approved"]])
            for quot in get_model("sale.quot").browse(quot_ids):
                if subj.find(quot.number.lower()) != -1:
                    quot_id = quot.id
                    break
            sale_ids = get_model("sale.order").search([["contact_id", "=", contact_id], ["state", "=", "confirmed"]])
            for sale in get_model("sale.order").browse(sale_ids):
                if subj.find(sale.number.lower()) != -1:
                    sale_id = sale.id
                    break
        if contact_id:
            name_id = "contact,%d" % contact_id
        elif lead_id:
            name_id = "sale.lead,%d" % lead_id
        if opport_id:
            related_id = "sale.opportunity,%d" % opport_id
        elif quot_id:
            related_id = "sale.quot,%d" % quot_id
        elif sale_id:
            related_id = "sale.order,%d" % sale_id
        elif contact_id:
            related_id = "contact,%d" % contact_id
        vals = {
            "type": "email",
            "subject": email["subject"],
            "state": "done",
            "user_id": user_id,
            "related_id": related_id,
            "name_id": name_id,
            "email_uid": email["msg_uid"],
            "email_account_id": email["account_id"],
            "body": email["body"],
            "date": email["date"],
        }
        act_id = get_model("activity").create(vals)
        print("  => new activity %d" % act_id)
        return act_id

    def get_overdue(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.due_date:
                vals[obj.id] = obj.due_date < time.strftime("%Y-%m-%d") and obj.state != "done"
            else:
                vals[obj.id] = False
        return vals

    def search_overdue(self, clause, context={}):
        return [["due_date", "<", time.strftime("%Y-%m-%d")], ["state", "!=", "done"]]

    def check_days_before_overdue(self, ids, days=None, days_from=None, days_to=None, context={}):
        print("Activity.check_days_before_overdue", ids, days, days_from, days_to)
        cond = [["state", "!=", "done"]]
        if days != None:
            d = (datetime.date.today() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            cond.append(["due_date", "=", d])
        if days_from != None:
            d = (datetime.date.today() + datetime.timedelta(days=days_from)).strftime("%Y-%m-%d")
            print("XXXXXXXXXXXXXxx d", d)
            cond.append(["due_date", "<=", d])
        if days_to != None:
            d = (datetime.date.today() + datetime.timedelta(days=days_to)).strftime("%Y-%m-%d")
            cond.append(["due_date", ">=", d])
        if ids:
            cond.append(["ids", "in", ids])
        ids = self.search(cond)
        return ids

Activity.register()
