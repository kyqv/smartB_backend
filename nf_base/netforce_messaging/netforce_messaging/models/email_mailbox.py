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
from netforce.utils import print_color
import smtplib
import poplib
import imaplib
import email
from email.utils import parseaddr, parsedate, formatdate
from email.header import decode_header
from datetime import *
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email.encoders import encode_base64
from email.header import Header
from netforce import utils
from netforce.access import get_active_user
from netforce.utils import print_color
import requests
import base64
import mimetypes
import json
import os
import socket

socket.setdefaulttimeout(15)


class Mailbox(Model):
    _name = "email.mailbox"
    _string = "Email Mailbox"
    _fields = {
        "name": fields.Char("Mailbox Name", required=True, search=True),
        "user_id": fields.Many2One("base.user", "User"),
        "type": fields.Selection([["in", "Inbox"], ["out", "Outbox"]], "Mailbox Type", required=True),
        "account_id": fields.Many2One("email.account", "Email Account"),
        "account_mailbox": fields.Char("Account Mailbox"),
        "last_msg_uid": fields.Char("Last Message UID"),
        "last_msg_date": fields.Date("Last Message Date"),
        "active": fields.Boolean("Active"),
    }
    _order = "name"
    _defaults = {
        "active": True,
    }

    def send_emails(self, ids, context={}):
        for email in get_model("email.message").search_browse([["state", "=", "to_send"], ["mailbox_id", "in", ids]], order="id"):
            email.send()

    def get_email_events(self, ids, context={}):
        obj = self.browse(ids)[0]
        acc = obj.account_id
        if not acc:
            raise Exception("Missing email account")
        if acc.type == "mailgun":
            obj.get_email_events_mailgun()
        else:
            raise Exception("Invalid account type")

    def get_email_events_mailgun(self, ids, context={}):
        print("get_email_events_mailgun", ids)
        obj = self.browse(ids)[0]
        acc = obj.account_id
        if not acc:
            raise Exception("Missing email account")
        if acc.type != "mailgun":
            raise Exception("Invalid email account type")
        url = "https://api.mailgun.net/v2/%s/events" % acc.user
        res = get_model("email.event").search([], order="date desc", limit=1)
        if res:
            last_event = get_model("email.event").browse(res[0])
            last_date = last_event.date
        else:
            last_event = None
            last_date = "2000-01-01 00:00:00"
        while True:
            data = {
                "ascending": "yes",
                "limit": 100,
            }
            d0 = datetime.strptime(last_date, "%Y-%m-%d %H:%M:%S")
            d0 = d0.timetuple()
            d0 = time.mktime(d0)
            d0 = formatdate(d0)
            data["begin"] = d0
            print("requesting events from mailgun...")
            print("data", data)
            r = requests.get(url, auth=("api", acc.password), params=data, timeout=10)
            # print("RES",r.text)
            res = json.loads(r.text)
            new_last_date = None
            ev_items = res["items"]
            for ev in ev_items:
                d = datetime.fromtimestamp(ev["timestamp"])
                ev_date = d.strftime("%Y-%m-%d %H:%M:%S")
                if not new_last_date or ev_date > new_last_date:
                    new_last_date = ev_date
                msg = ev.get("message")
                if not msg:
                    continue
                msg_id = msg["headers"]["message-id"]
                msg_id = "<" + msg_id + ">"
                res = get_model("email.message").search([["mailbox_id", "=", obj.id], ["message_id", "=", msg_id]])
                if not res:
                    print("WARNING: Email not found: %s" % msg_id)
                    continue
                email_id = res[0]
                email = get_model("email.message").browse(email_id)
                vals = {
                    "email_id": email_id,
                    "date": ev_date,
                    "ip_addr": ev.get("ip"),
                    "url": ev.get("url"),
                }
                if last_event and vals["date"] <= last_event.date and vals["email_id"] == last_event.email_id.id:  # XXX
                    print("Event already imported: %s" % last_event.id)
                    continue
                geo = ev.get("geolocation")
                if geo:
                    vals["location"] = "%(city)s/%(region)s/%(country)s" % geo
                client = ev.get("client-info")
                if client:
                    vals["user_agent"] = client["user-agent"]
                vals["type"] = ev["event"]
                delivery = ev.get("delivery-status")
                if delivery:
                    vals["details"] = delivery.get("message") or delivery.get("description")
                get_model("email.event").create(vals)
                if vals["type"] == "opened":
                    email.write({"opened": True})
                elif vals["type"] == "clicked":
                    email.write({"clicked": True})
                elif vals["type"] == "delivered":
                    email.write({"state": "delivered"})
                elif vals["type"] == "failed":
                    email.write({"state": "bounced"})
                    get_model("email.reject").add_to_black_list(ev["recipient"], reason="bounced")
                elif vals["type"] == "rejected":
                    email.write({"state": "rejected"})
                    get_model("email.reject").add_to_black_list(ev["recipient"], reason="rejected")
                elif vals["type"] == "unsubscribed":
                    email.write({"state": "rejected"})
                    get_model("email.reject").add_to_black_list(ev["recipient"], reason="unsubscribed")
                elif vals["type"] == "complained":
                    email.write({"state": "rejected"})
                    get_model("email.reject").add_to_black_list(ev["recipient"], reason="complained")
            if len(ev_items) < 100:
                break
            last_date = new_last_date

    def fetch_all_emails(self, context={}):
        ids = self.search([["account_id.type", "in", ["pop", "imap"]]])
        self.fetch_emails(ids,context=context)

    def fetch_emails(self, ids, context={}):
        res = None
        for obj in self.browse(ids):
            acc = obj.account_id
            if not acc:
                raise Exception("Missing email account")
            if acc.type == "pop":
                res = obj.fetch_emails_pop(context=context)
            elif acc.type == "imap":
                res = obj.fetch_emails_imap(context=context)
        return res

    def fetch_emails_pop(self, ids, context={}):
        print("fetch_emails_pop", ids)
        for obj in self.browse(ids):
            acc = obj.account_id
            if not acc:
                raise Exception("Missing email account")
            if acc.type != "pop":
                raise Exception("Invalid email account type")
            if acc.security == "ssl":
                serv = poplib.POP3_SSL(acc.host, acc.port)
            else:
                serv = poplib.POP3(acc.host, acc.port)
            serv.user(acc.user)
            if acc.password:
                serv.pass_(acc.password)
            try:
                resp, msg_list, size = serv.uidl()
                for msg_info in msg_list:
                    msg_no, msg_uid = msg_info.decode().split()
                    try:
                        res = get_model("email.message").search_read(
                            [["mailbox_id", "=", obj.id], ["mailbox_message_uid", "=", msg_uid]])
                        if res:
                            serv.dele(msg_no)
                            continue
                        resp, lines, size = serv.retr(msg_no)
                        email_str = b"\n".join(lines)
                        get_model("email.message").create_from_string(email_str, mailbox_id=obj.id)
                    except Exception as e:
                        print("WARNING: failed to import email %s" % msg_uid)
                        import traceback
                        traceback.print_exc()
                    finally:
                        serv.dele(msg_no)
                        pass
            finally:
                serv.quit()
        return {
            "flash": "Emails fetched successfully"
        }

    def fetch_emails_imap(self, ids, context={}):
        print("fetch_emails_imap", ids)
        for obj in self.browse(ids):
            acc = obj.account_id
            if not acc:
                raise Exception("Missing email account")
            if acc.type != "imap":
                raise Exception("Invalid email account type")
            if acc.security == "ssl":
                serv = imaplib.IMAP4_SSL(host=acc.host, port=acc.port or 993)
            else:
                serv = imaplib.IMAP4(host=acc.host, port=acc.port or 143)
            serv.login(acc.user, acc.password)
            if not obj.account_mailbox:
                raise Exception("Account mailbox name missing")
            res = serv.select('"%s"' % obj.account_mailbox)
            if res[0] != "OK":
                raise Exception("Account mailbox '%s' not found on server" % obj.account_mailbox)
            if obj.last_msg_uid:
                try:
                    last_msg_uid = int(obj.last_msg_uid)
                    res = serv.fetch("%s:*" % last_msg_uid, "(UID)")
                    msg_ids = [int(r.split()[0]) for r in res[1]]
                    msg_ids = [x for x in msg_ids if x > last_msg_uid]
                except: # XXX
                    print("WARNING: failed to get messages by last UID")
                    if obj.last_msg_date:
                        d = datetime.strptime(obj.last_msg_date, "%Y-%m-%d")
                        t0 = d.strftime("%d-%b-%Y")
                        res = serv.search(None, '(SINCE "%s")' % t0)
                        msg_ids = [int(x) for x in res[1][0].split()]
                    else:
                        raise Exception("Failed to fetch emails (IMAP)")
            elif obj.last_msg_date:
                d = datetime.strptime(obj.last_msg_date, "%Y-%m-%d")
                t0 = d.strftime("%d-%b-%Y")
                res = serv.search(None, '(SINCE "%s")' % t0)
                msg_ids = [int(x) for x in res[1][0].split()]
            else:
                raise Exception("Missing starting message UID or date")
            for i, msg_id in enumerate(msg_ids):
                print("fetch imap email %d/%d" % (i, len(msg_ids)))
                res = serv.fetch(str(msg_id), "(BODY.PEEK[] INTERNALDATE)")
                email_str = res[1][0][1]
                email_id=get_model("email.message").create_from_string(
                    email_str, mailbox_id=obj.id, mailbox_message_uid=str(msg_id), context=context)
                get_model("email.message").link_emails([email_id])
                get_model("email.message").trigger([email_id],"received")
            if msg_ids:
                vals = {
                    "last_msg_uid": str(msg_ids[-1]),
                    "last_msg_date": time.strftime("%Y-%m-%d"),  # FIXME: get last msg internal date
                }
                obj.write(vals)
        print("fetch emails done")
        return {
            "flash": "Emails fetched successfully",
        }

    def get_flags_imap(self, ids, context={}):
        print("get_flags_imap", ids)
        for obj in self.browse(ids):
            acc = obj.account_id
            if not acc:
                raise Exception("Missing email account")
            if acc.type != "imap":
                raise Exception("Invalid email account type")
            if acc.security == "ssl":
                serv = imaplib.IMAP4_SSL(host=acc.host, port=acc.port or 993)
            else:
                serv = imaplib.IMAP4(host=acc.host, port=acc.port or 143)
            serv.login(acc.user, acc.password)
            if not obj.account_mailbox:
                raise Exception("Account mailbox name missing")
            res = serv.select('"%s"' % obj.account_mailbox)
            if res[0] != "OK":
                raise Exception("Account mailbox '%s' not found on server" % obj.account_mailbox)
            res = serv.search(None, '(SINCE "01-Oct-2014")')
            msg_ids = [int(x) for x in res[1][0].decode().split()]
            if not msg_ids:
                continue
            res = serv.fetch(",".join(str(x) for x in msg_ids), "(FLAGS)")
            open_msg_ids = []
            for l in res[1]:
                l = l.decode()
                msg_id = l.partition(" ")[0]
                if l.find("Seen") != -1:
                    open_msg_ids.append(str(msg_id))
            print("open_msg_ids", open_msg_ids)
            email_ids = get_model("email.message").search([["mailbox_id", "=", obj.id], [
                "or", ["opened", "=", None], ["opened", "=", False]], ["mailbox_message_uid", "in", open_msg_ids]])
            print("email_ids", email_ids)
            get_model("email.message").write(email_ids, {"opened": True})

Mailbox.register()
