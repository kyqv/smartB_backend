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


class Account(Model):
    _name = "email.account"
    _string = "Email Account"
    _name_field = "name"
    _fields = {
        "name": fields.Char("Account Name", required=True, search=True),
        "type": fields.Selection([["nf_mail","Netforce Mail"], ["imap", "IMAP"], ["pop", "POP"], ["smtp", "SMTP"], ["mailgun", "Mailgun"]], "Type", required=True, search=True),
        "host": fields.Char("Host"),
        "port": fields.Integer("Port"),
        "user": fields.Char("User"),
        "password": fields.Char("Password"),
        "security": fields.Selection([["starttls", "STARTTLS"], ["ssl", "SSL"]], "Security"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "mailboxes": fields.One2Many("email.mailbox", "account_id", "Mailboxes"),
    }

    def list_imap_mailboxes(self, ids, context={}):
        print("fetch_emails_imap", ids)
        obj = self.browse(ids)[0]
        if obj.type != "imap":
            raise Exception("Invalid email account type")
        if obj.security == "ssl":
            serv = imaplib.IMAP4_SSL(host=obj.host, port=obj.port or 993)
        else:
            serv = imaplib.IMAP4(host=obj.host, port=obj.port or 143)
        serv.login(obj.user, obj.password)
        res = serv.list()
        if res[0] != "OK":
            raise Exception("Invalid IMAP response")
        return {
            "flash": "Mailboxes found on IMAP server: " + ", ".join(m.decode() for m in res[1]),
        }

Account.register()
