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
import smtplib
import email
from email.utils import parseaddr, parsedate_tz, formatdate, getaddresses
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email.encoders import encode_base64
from email.header import Header
from email.header import decode_header
from netforce import utils
from netforce.access import get_active_user
from netforce import access
from netforce.utils import print_color
import re
import os
import base64
import string
from netforce.database import get_active_db
from netforce import database
from datetime import *
import time
import requests
import mimetypes
import json


def conv_charset(charset):
    if charset == "windows-874":
        charset = "cp874"
    return charset


class EmailMessage(Model):
    _name = "email.message"
    _string = "Email Message"
    _name_field = "message_id"
    _fields = {
        "type": fields.Selection([["in", "Incoming"], ["out", "Outgoing"]], "Type"),  # XXX: deprecated
        "date": fields.DateTime("Date", required=True, search=True, readonly=True),
        "from_addr": fields.Char("From", required=True, search=True, size=4096),
        "reply_to": fields.Char("Reply To",search=True,size=4096),
        "to_addrs": fields.Char("To", size=4096, search=True),
        "cc_addrs": fields.Char("Cc", size=4096, search=True),
        "subject": fields.Char("Subject", required=True, size=4096, search=True),
        # XXX: deprecated
        "content_type": fields.Selection([["plain", "Plain Text"], ["html", "HTML"]], "Content Type"),
        "body": fields.Text("Body", search=True),
        "state": fields.Selection([["draft", "Draft"], ["to_send", "To Send"], ["sent", "Sent"], ["delivered", "Delivered"], ["bounced", "Bounced"], ["rejected", "Rejected"], ["received", "Received"], ["error", "Error"]], "Status", required=True, search=True),
        "message_id": fields.Char("Message ID", size=4096, readonly=True),
        "mailbox_message_uid": fields.Char("Mailbox Message UID"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "name_id": fields.Reference([["contact", "Contact"], ["sale.lead", "Sales Lead"], ["mkt.target", "Marketing Target"]], "Contact Person", search=True),
        "related_id": fields.Reference([["sale.lead","Sales Lead"], ["sale.opportunity", "Sales Opportunity"], ["sale.quot", "Quotation"], ["sale.order", "Sales Order"], ["job", "Service Order"], ["purchase.order", "Purchase Order"], ["account.invoice", "Invoice"], ["mkt.campaign", "Marketing Campaign"], ["ecom.cart","Ecommerce Cart"]], "Related To"),
        "attachments": fields.One2Many("email.attach", "email_id", "Attachments"),
        "events": fields.One2Many("email.event", "email_id", "Email Events"),
        "opened": fields.Boolean("Opened", readonly=True, search=True),
        "clicked": fields.Boolean("Link Clicked", readonly=True, search=True),
        "in_reject_list": fields.Boolean("Black Listed", function="check_reject_list"),
        "parent_uid": fields.Char("Parent Unique ID", readonly=True, size=4096),  # XXX
        "parent_id": fields.Many2One("email.message", "Parent"),
        "mailbox_id": fields.Many2One("email.mailbox", "Mailbox", required=True, search=True),
        "open_detect": fields.Boolean("Open Detect", function="get_open_detect"),
        "num_attach": fields.Integer("# Attach.", function="get_num_attach"),
        "error_message": fields.Text("Error Message"),
        "template_id": fields.Many2One("email.template","Email Template"),
        "source": fields.Text("Email Source"),
        "orig_from_addr": fields.Char("Original From",size=4096),
        "is_spam": fields.Boolean("Is Spam"),
    }
    _order = "date desc"

    def _get_mailbox(self, context={}):
        user_id = get_active_user()
        res = get_model("email.mailbox").search([["type", "=", "out"]], order="id")
        if not res:
            return None
        return res[0]

    def _get_from_addr(self, context={}):
        user_id = get_active_user()
        user = get_model("base.user").browse(user_id)
        return user.email

    def _get_to_addrs(self, context={}):
        defaults = context.get("defaults")
        if not defaults:
            return None
        res = defaults.get("parent_id")
        if not res:
            return None
        parent_id=int(res)
        parent = get_model("email.message").browse(parent_id)
        return parent.from_addr

    def _get_subject(self, context={}):
        defaults = context.get("defaults")
        if not defaults:
            return None
        res = defaults.get("parent_id")
        if not res:
            return None
        parent_id=int(res)
        parent = get_model("email.message").browse(parent_id)
        s = parent.subject
        return "Re: " + s

    def _get_body(self, context={}):
        defaults = context.get("defaults")
        if not defaults:
            return None
        res = defaults.get("parent_id")
        if not res:
            return None
        parent_id=int(res)
        parent = get_model("email.message").browse(parent_id)
        d = datetime.strptime(parent.date, "%Y-%m-%d %H:%M:%S")
        pbody = parent.body
        m = re.search("<body>(.*)</body>", pbody, re.DOTALL)
        if m:
            pbody = m.group(1)
        m = re.search("<BODY>(.*)</BODY>", pbody, re.DOTALL)
        if m:
            pbody = m.group(1)
        body = "<div>On %s, %s wrote:" % (d.strftime("%a, %b %d, %Y at %H:%M"), parent.from_addr)
        body += '<blockquote style="margin:0 0 0 .8ex;border-left:1px #ccc solid;padding-left:1ex">' + \
            pbody + "</blockquote>"
        body += "</div>"
        return body

    _defaults = {
        "type": "out",
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "mailbox_id": _get_mailbox,
        "from_addr": _get_from_addr,
        "to_addrs": _get_to_addrs,
        "subject": _get_subject,
        "body": _get_body,
    }

    def to_send(self, ids, context={}):
        for obj in self.browse(ids):
            obj.write({"state": "to_send"})

    def to_draft(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state": "draft"})

    def send_emails(self, context={}):  # FIXME
        print("send_emails")
        mailbox_ids = get_model("email.mailbox").search([["account_id.type", "in", ["smtp", "mailgun", "nf_mail"]]])
        get_model("email.mailbox").send_emails(mailbox_ids)

    def check_sent_emails(self, context={}):
        print("send_sent_emails")
        res = get_model("email.account").search([["type", "=", "mailgun"]])  # XXX
        if not res:
            return
        acc_id = res[0]
        get_model("email.account").check_sent_emails([acc_id])

    def send_from_template(self, template=None, from_addr=None, to_addrs=None, context={}):
        if not template:
            raise Exception("Missing template")
        res = get_model("email.template").search([["name", "=", template]])
        if not res:
            raise Exception("Template not found: %s" % template)
        tmpl_id = res[0]
        tmpl = get_model("email.template").browse(tmpl_id)
        trigger_model = context.get("trigger_model")
        if not trigger_model:
            raise Exception("Missing trigger model")
        tm = get_model(trigger_model)
        trigger_ids = context.get("trigger_ids")
        if trigger_ids is None:
            raise Exception("Missing trigger ids")
        user_id = get_active_user()
        if user_id:
            user = get_model("base.user").browse(user_id)
        else:
            user = None
        for obj in tm.browse(trigger_ids):
            tmpl_ctx = {"obj": obj, "user": user, "context": context}
            get_model("email.template").create_email([tmpl_id],tmpl_ctx)
        self.send_emails_async()
    
    def send_from_template_multi(self, template=None, profile_codes=None, user_names=None, context={}):
        if not template:
            raise Exception("Missing template")
        if profile_codes:
            profile_ids = get_model("profile").search([["code","in",profile_codes]])
            users = get_model("base.user").search_browse([["profile_id","in",profile_ids]])
        elif user_names:
            users = get_model("base.user").search_browse([["name","in",user_names]])
        for user in users:
            if user.email is None:
                continue
            else:
                context["email"] = user.email
                self.send_from_template(template=template,context=context)

    def import_email(self, vals):
        print("import_email from=%s to=%s cc=%s subject=%s" %
              (vals["from_addr"], vals.get("to_addrs"), vals.get("cc_addrs"), vals["subject"]))

        def _check_addr(addrs):
            if not addrs:
                return False
            addr_list = addrs.split(",")
            for addr in addr_list:
                addr = addr.strip()
                res = get_model("base.user").search([["email", "=ilike", addr]])
                if res:
                    return True
                res = get_model("contact").search([["email", "=ilike", addr]])
                if res:
                    return True
                res = get_model("sale.lead").search([["email", "=ilike", addr]])
                if res:
                    return True
            return False
        if not _check_addr(vals["from_addr"]):
            print_color("email ignored: unknown 'from' address: %s" % vals["from_addr"], "red")
            return None
        if not _check_addr(vals.get("to_addrs")) and not _check_addr(vals.get("cc_addrs")):
            print_color("email ignored: unknown 'to' and 'cc' address: to=%s cc=%s" %
                        (vals.get("to_addrs"), vals.get("cc_addrs")), "red")
            return None
        new_id = self.create(vals)
        print_color("email imported: id=%d" % new_id, "green")
        self.link_emails([new_id])
        self.trigger([new_id], "received")
        return new_id

    def link_emails(self, ids, context={}):
        pass

    def check_reject_list(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            rejected = False
            if not obj.to_addrs:
                raise Exception("Missing To: address")
            for addr in obj.to_addrs.split(","):
                addr = addr.strip()
                res = get_model("email.reject").search([["email", "=", addr]])
                if res:
                    rejected = True
                    break
            vals[obj.id] = rejected
        return vals

    def create_from_string(self, email_str, mailbox_id=None, mailbox_message_uid=None, context={}):
        print("email.message create_from_string (%d bytes)" % len(email_str), mailbox_message_uid)
        msg = email.message_from_bytes(email_str)
        msg_id = msg.get("message-id")
        print("msg_id", msg_id)
        res = get_model("email.message").search([["mailbox_id", "=", mailbox_id], ["message_id", "=", msg_id]])
        if res:
            return res[0]

        def dec_header(data):
            dh = decode_header(data or "")
            s = ""
            for data, charset in dh:
                if isinstance(data, str):
                    s += data
                else:
                    try:
                        s += data.decode(conv_charset(charset) or "utf-8")
                    except:
                        s += data.decode("utf-8", errors="replace")
            return s

        def dec_date(data):
            print("dec_date", data)
            res = parsedate_tz(data or "")
            if not res:
                return time.strftime("%Y-%m-%d %H:%M:%S")
            d = datetime.fromtimestamp(email.utils.mktime_tz(res))
            return d.strftime("%Y-%m-%d %H:%M:%S")
        body_text = []
        body_html = []
        attachments = []
        content_ids = {}
        for i, part in enumerate(msg.walk()):
            print("-" * 80)
            print("part #%d" % i)
            c_type = part.get_content_type()
            print("c_type", c_type)
            c_disp = part.get("Content-Disposition")
            print("c_disp", c_disp)
            c_id = part.get("Content-ID")
            print("c_id", c_id)
            if c_disp:
                fname = part.get_filename()
                data = part.get_payload(decode=True)
                attachments.append((fname, data))
            elif c_id:
                data = part.get_payload(decode=True)
                rand = base64.urlsafe_b64encode(os.urandom(8)).decode()
                fname = "email-inline-content," + rand
                if c_type == "image/png":
                    ext = ".png"
                elif c_type == "image/jpeg":
                    ext = ".jpg"
                elif c_type == "image/gif":
                    ext = ".gif"
                else:
                    ext = None
                if ext:
                    fname += "." + ext
                content_ids[c_id] = (fname, data)
            else:
                if c_type == "text/plain":
                    v = part.get_payload(decode=True).decode(errors="replace")
                    body_text.append(v)
                elif c_type == "text/html":
                    v = part.get_payload(decode=True).decode(errors="replace")
                    body_html.append(v)
                else:
                    continue
        if body_html:
            body = body_html[0]
        elif body_text:
            body = "<html><body>"
            for t in body_text:
                body += "<pre>" + t + "</pre>"
            body += "</body></html>"
        else:
            body = ""

        def _replace(m):
            cid = m.group(1)
            cid = "<" + cid + ">"
            if cid not in content_ids:
                return m.group(0)
            fname = content_ids[cid][0]
            dbname = get_active_db()
            return "/static/db/" + dbname + "/files/" + fname
        body = re.sub('"cid:(.*?)"', _replace, body)
        subject=dec_header(msg["subject"]).replace("\r","").replace("\n","")[:4096]
        from_addr=dec_header(msg["from"])
        from_name,from_email=parseaddr(from_addr)
        source=email_str.decode("utf-8",errors="replace")
        orig_from=None
        if re.search("Fwd?:",subject,re.I):
            matches=re.findall(r"From: (.*?)([\w\.-]+@[\w\.-]+)",source,re.MULTILINE)
            if matches:
                found=False
                for m in matches:
                    prefix,orig_from_email=m
                    if orig_from_email==from_email:
                        continue
                    found=True
                    break
                if found:
                    m=re.search(r"^\w+( \w+)*",prefix)
                    if m:
                        orig_from_name=m.group(0) 
                    else:
                        orig_from_name=None
                    if orig_from_name:
                        orig_from=orig_from_name+" "
                    else:
                        orig_from=""
                    orig_from+="<%s>"%orig_from_email
        email_vals = {
            "type": "in",
            "state": "received",
            "date": dec_date(msg["date"]),
            "from_addr": from_addr,
            "subject": subject,
            "body": body,
            "message_id": msg_id,
            "parent_uid": msg.get("in-reply-to"),
            "mailbox_id": mailbox_id,
            "mailbox_message_uid": mailbox_message_uid,
            "source": source,
            "orig_from_addr": orig_from,
        }
        if msg.get_all("to"):
            email_vals["to_addrs"] = ", ".join([x[1] for x in getaddresses(msg.get_all("to"))])
        if msg.get_all("cc"):
            email_vals["cc_addrs"] = ", ".join([x[1] for x in getaddresses(msg.get_all("cc"))])
        email_id = get_model("email.message").create(email_vals)
        if not context.get("no_attach"):
            for fname, data in attachments:
                try:
                    if not fname:
                        continue
                    rand = base64.urlsafe_b64encode(os.urandom(8)).decode()
                    res = os.path.splitext(fname)
                    basename="".join(filter(lambda c: c in string.printable, res[0]))
                    basename="attach-"+basename[:64]
                    fname2 = basename + "," + rand + res[1]
                    path=utils.get_file_path(fname2)
                    open(path, "wb").write(data or b"")
                    vals = {
                        "email_id": email_id,
                        "file": fname2,
                    }
                    get_model("email.attach").create(vals)
                except Exception as e:
                    print("WARNING: failed to save attachment: %s"%e)
            for fname, data in content_ids.values():
                dbname = get_active_db()
                fdir = os.path.join("static", "db", dbname, "files")
                if not os.path.exists(fdir):
                    os.makedirs(fdir)
                path = os.path.join(fdir, fname)
                open(path, "wb").write(data)
        return email_id

    def reply(self, ids, context={}):
        obj = self.browse(ids)[0]
        return {
            "next": {
                "name": "email",
                "mode": "form",
                "defaults": {
                    "parent_id": obj.id,
                },
            }
        }

    def get_open_detect(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.mailbox_id and obj.mailbox_id.type == "in":
                obj.write({"opened": True})
            vals[obj.id] = None
        return vals

    def forward_email(self, ids, vals, context={}):
        obj=self.browse(ids[0])
        vals["mailbox_id"]=self._get_mailbox()
        new_id=obj._copy(vals)[0]
        for attach in obj.attachments:
            vals={
                "email_id": new_id,
                "file": attach.file,
            }
            get_model("email.attach").create(vals)
        return new_id

    def send(self, ids, context={}):
        print("EmailMessage.send", ids)
        for obj in self.browse(ids):
            if obj.state not in ("draft","to_send"):
                continue
            if not obj.to_addrs.strip():
                obj.write({"state": "error"})
                continue
            mailbox = obj.mailbox_id
            if not mailbox:
                raise Exception("Missing mailbox in email %s" % obj.id)
            account = mailbox.account_id
            if not account:
                raise Exception("Missing account in mailbox %s of email %s" % (mailbox.name, obj.id))
            if obj.in_reject_list:
                print("WARNING: email in reject list: %s" % obj.id)
                obj.write({"state": "rejected"})
                continue
            if not utils.check_email_syntax(obj.from_addr):
                raise Exception("Invalid from address")
            if account.type == "smtp":
                obj.send_email_smtp()
            elif account.type == "mailgun":
                obj.send_email_mailgun()
            elif account.type == "nf_mail":
                obj.send_email_nf()
            else:
                raise Exception("Invalid email account type")
        #return {
        #    "next": {
        #        "name": "email",
        #        "tab_no": 1,
        #    },
        #}

    def send_email_smtp(self, ids, context={}):
        print("send_email_smtp", ids)
        obj = self.browse(ids)[0]
        if obj.state not in ("draft","to_send"):
            return
        try:
            mailbox = obj.mailbox_id
            if not mailbox:
                raise Exception("Missing mailbox")
            account = mailbox.account_id
            if account.type != "smtp":
                raise Exception("Invalid email account type")
            print("host: %s, port: %s"%(account.host,account.port))
            if account.security == "ssl":
                print("SSL")
                server = smtplib.SMTP_SSL(account.host, account.port or 465, timeout=30)
            else:
                server = smtplib.SMTP(account.host, account.port or 587, timeout=30)
            print("send helo")
            server.ehlo()
            if account.security == "starttls":
                server.starttls()
            print("login")
            if account.user:
                server.login(account.user, account.password)
            print("login success")
            msg = MIMEMultipart()
            msg.set_charset("utf-8")
            msg["From"] = obj.from_addr
            if obj.reply_to:
                msg["Reply-To"]=obj.reply_to
            msg["To"] = obj.to_addrs
            if obj.cc_addrs:
                msg["Cc"] = obj.cc_addrs
            msg["Subject"] = Header(obj.subject, "utf-8")
            msg.attach(MIMEText(obj.body, "html", "utf-8"))
            for attach in obj.attachments:
                path = utils.get_file_path(attach.file)
                data = open(path, "rb").read()
                part = MIMEBase('application', "octet-stream")
                part.set_payload(data)
                encode_base64(part)
                fname=utils.clean_filename(attach.file)
                part.add_header('Content-Disposition', 'attachment; filename="%s"' % fname)
                msg.attach(part)
            to_addrs = obj.to_addrs.split(",")
            cc_addrs = obj.cc_addrs.split(",") if obj.cc_addrs else []
            server.sendmail(obj.from_addr, to_addrs+cc_addrs, msg.as_string())
            #server.sendmail(account.user, to_addrs+cc_addrs, msg.as_string()) # TODO: check this
            obj.write({"state": "sent"})
            db=database.get_connection()
            db.commit()
            server.quit()
        except Exception as e:
            print("WARNING: failed to send email %s" % obj.id)
            import traceback
            traceback.print_exc()
            obj.write({"state": "error", "error_message": str(e)})

    def send_email_nf(self, ids, context={}):
        print("send_email_nf", ids)
        acc={
            "host": "smtp.sparkpostmail.com",
            "user": "SMTP_Injection",
            "password": "7fe52cc6414be1b6e865ac8afdf5fa051978c12b", # TODO: remove this from module
        }
        obj = self.browse(ids)[0]
        if obj.state not in ("draft","to_send"):
            return
        try:
            mailbox = obj.mailbox_id
            if not mailbox:
                raise Exception("Missing mailbox")
            account = mailbox.account_id
            if account.type != "nf_mail":
                raise Exception("Invalid email account type")
            server = smtplib.SMTP(acc["host"], 587, timeout=30)
            server.ehlo()
            server.starttls()
            print("login")
            server.login(acc["user"], acc["password"])
            print("login success")
            msg = MIMEMultipart()
            msg.set_charset("utf-8")
            msg["From"] = obj.from_addr
            if obj.reply_to:
                msg["Reply-To"]=obj.reply_to
            msg["To"] = obj.to_addrs
            if obj.cc_addrs:
                msg["Cc"] = obj.cc_addrs
            msg["Subject"] = Header(obj.subject, "utf-8")
            msg.attach(MIMEText(obj.body, "html", "utf-8"))
            for attach in obj.attachments:
                path = utils.get_file_path(attach.file)
                data = open(path, "rb").read()
                part = MIMEBase('application', "octet-stream")
                part.set_payload(data)
                encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="%s"' % attach.file)
                msg.attach(part)
            to_addrs = obj.to_addrs.split(",")
            cc_addrs = obj.cc_addrs.split(",") if obj.cc_addrs else []
            server.sendmail(obj.from_addr, to_addrs+cc_addrs, msg.as_string())
            obj.write({"state": "sent"})
            server.quit()
        except Exception as e:
            print("WARNING: failed to send email %s" % obj.id)
            import traceback
            traceback.print_exc()
            obj.write({"state": "error", "error_message": str(e)})

    def send_email_mailgun(self, ids, context={}):
        print("send_emails_mailgun", ids)
        obj = self.browse(ids)[0]
        if obj.state not in ("draft","to_send"):
            return
        try:
            mailbox = obj.mailbox_id
            if not mailbox:
                raise Exception("Missing mailbox")
            account = mailbox.account_id
            if account.type != "mailgun":
                raise Exception("Invalid email account type")
            url = "https://api.mailgun.net/v2/%s/messages" % account.user
            to_addrs = []
            for a in obj.to_addrs.split(","):
                a = a.strip()
                if not utils.check_email_syntax(a):
                    raise Exception("Invalid email syntax: %s" % a)
                to_addrs.append(a)
            if not to_addrs:
                raise Exception("Missing recipient address")
            data = {
                "from": obj.from_addr,
                "to": to_addrs,
                "subject": obj.subject,
            }
            if obj.cc_addrs:
                data["cc"] = [a.strip() for a in obj.cc_addrs.split(",")]
            data["html"] = obj.body or "<html><body></body></html>"
            files = []
            for attach in obj.attachments:
                path = utils.get_file_path(attach.file)
                f = open(path, "rb")
                files.append(("attachment", f))
            r = requests.post(url, auth=("api", account.password), data=data, files=files,timeout=15)
            try:
                res = json.loads(r.text)
                msg_id = res["id"]
            except:
                raise Exception("Invalid mailgun response: %s" % r.text)
            obj.write({"state": "sent", "message_id": msg_id})
        except Exception as e:
            print("WARNING: failed to send email %s" % obj.id)
            import traceback
            traceback.print_exc()
            obj.write({"state": "error", "error_message": str(e)})

    def get_emails(self, context={}):
        print("EmailMessage.get_emails")
        for mailbox in get_model("email.mailbox").search_browse([]):
            acc = mailbox.account_id
            if not acc:
                continue
            if acc.type == "imap":
                mailbox.fetch_emails_imap()
                #mailbox.get_flags_imap()
            elif acc.type == "pop":
                mailbox.fetch_emails_pop()
            elif acc.type == "mailgun":
                mailbox.get_email_events_mailgun()
        return {
            "next": {
                "name": "email",
                "tab_no": 0,
            },
        }

    def mark_opened(self, ids, context={}):
        self.write(ids, {"opened": True})

    def get_num_attach(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            vals[obj.id] = len(obj.attachments)  # XXX: speed
        return vals

    def send_emails_async(self, context={}):
        vals={
            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "model": "email.message",
            "method": "send_emails",
        }
        get_model("bg.task").create(vals)

    # XXX: deprecated
    def exec_rules(self, ids, context={}):
        print("EmailMessage.exec_rules",ids)
        for obj in self.browse(ids):
            for rule in get_model("email.rule").search_browse([]):
                print("checking rule %s"%rule.sequence)
                rule_match=True
                if rule.mailbox_id and obj.mailbox_id.id!=rule.mailbox_id.id:
                    rule_match=False
                    print("  wrong mailbox")
                if rule.from_addr:
                    m=re.search(rule.from_addr,obj.from_addr,re.I)
                    if not m:
                        rule_match=False
                        print("  wrong from_addr")
                if rule.to_addr:
                    m=re.search(rule.to_addr,obj.to_addrs or "",re.I)
                    if not m:
                        rule_match=False
                        print("  wrong to_addr")
                if rule.subject:
                    m=re.search(rule.subject,obj.subject,re.I)
                    if not m:
                        rule_match=False
                        print("  wrong subject")
                if rule.body:
                    m=re.search(rule.body,obj.body,re.I)
                    if not m:
                        rule_match=False
                        print("  wrong body")
                if rule_match:
                    print("  match")
                    print("  ==> %s"%rule.action)
                    if rule.action=="spam":
                        obj.write({"is_spam": True})
                    elif rule.action=="copy_to_lead":
                        obj.copy_to_lead()
                    elif rule.action=="convert_lead":
                        obj.convert_lead()
                    break

    def submit_contact_form(self,name,email,subject,message,context={}):
        if not name:
            raise Exception("Missing name")
        if not email:
            raise Exception("Missing email")
        if not utils.check_email_syntax(email):
            raise Exception("Invalid email")
        vals={
            "name": name,
            "email": email,
            "subject": subject,
            "message": message,
        }
        res=get_model("email.template").search([["name","=","contact_form"]])
        if not res:
            raise Exception("Email template not found: contact_form")
        tmpl_id=res[0]
        get_model("email.template").create_email([tmpl_id],data=vals)
        self.send_emails_async()

    def delete_unlinked_emails(self,context={}):
        ids=self.search([["name_id","=",None],["related_id","=",None]])
        self.delete(ids)

    def check_email(self,ids,**kw):
        match_ids=[]
        for obj in self.browse(ids):
            if kw.get("mailbox"):
                if not obj.mailbox_id or obj.mailbox_id.name!=kw["mailbox"]:
                    continue
            if kw.get("from"):
                if not obj.from_addr or obj.from_addr.find(kw["from"])==-1:
                    continue
            if kw.get("to"):
                if not obj.to_addrs or obj.to_addrs.find(kw["to"])==-1:
                    continue
            if kw.get("cc"):
                if not obj.cc_addrs or obj.cc_addrs.find(kw["cc"])==-1:
                    continue
            if kw.get("subject"):
                if not obj.subject or obj.subject.find(kw["subject"])==-1:
                    continue
            match_ids.append(obj.id)
        return match_ids

    def mark_as_spam(self,context={}):
        ids=context["trigger_ids"]
        self.write(ids,{"is_spam": True})

    def send_email_from_preview(self,model=None,active_id=None,email_params=None,email_page_id=None,attach_page_id=None,attach_report_id=None,context={}):
        if not active_id:
            raise Exception("Missing active_id")
        if not email_page_id:
            raise Exception("Missing email_page_id")
        if not attach_page_id:
            raise Exception("Missing attach_page_id")
        res=utils.render_page_html(page_id=email_page_id,active_id=active_id)
        body=res["data"]
        if attach_page_id:
            res=utils.render_page_pdf(page_id=attach_page_id,active_id=active_id)
            attach_data=res["data"]
            attach_fname=res.get("filename")
        elif attach_report_id:
            res=utils.render_report_pdf(attach_report_id,active_id)
            attach_data=res["data"]
            attach_fname=res.get("filename")
        else:
            attach_data=None
            attach_fname=None
        mailbox_id=1 # XXX
        user_id=access.get_active_user()
        company_id=access.get_active_company()
        vals={
            "from_addr": email_params.get("from_addr"),
            "to_addrs": email_params.get("to_addrs"),
            "subject": email_params.get("subject"),
            "body": body,
            "mailbox_id": mailbox_id,
            "user_id": user_id,
            "company_id": company_id,
        }
        if attach_data:
            if not attach_fname:
                attach_fname="report.pdf"
            attach_fname_rand=utils.get_random_filename(attach_fname)
            path=utils.get_file_path(attach_fname_rand)
            open(path,"wb").write(attach_data)
            attach_vals={
                "file": attach_fname_rand,
            }
            vals["attachments"]=[("create",attach_vals)]
        access.set_active_user(1) # XXX
        email_id=self.create(vals)
        self.send([email_id])
        return email_id

EmailMessage.register()
