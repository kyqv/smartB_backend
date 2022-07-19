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
import time
from netforce import utils
import smtplib


class TargetList(Model):
    _name = "mkt.target.list"
    _string = "Target List"
    _name_field = "name"
    _fields = {
        "name": fields.Char("Target List Name", required=True, search=True),
        "date": fields.Date("Date Created", required=True, search=True),
        "targets": fields.One2Many("mkt.target", "list_id", "Targets"),
        "num_targets": fields.Integer("Number of targets", function="get_num", function_multi=True),
        "num_emails_verified": fields.Integer("Number of verified emails", function="get_num", function_multi=True),
        "num_emails_error": fields.Integer("Number of error emails", function="get_num", function_multi=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
    }
    _order = "date desc"
    _defaults = {
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }

    def get_num(self, ids, context={}):
        db = database.get_connection()
        res = db.query("SELECT list_id,count(*) FROM mkt_target WHERE list_id IN %s GROUP BY list_id", tuple(ids))
        vals = {}
        for id in ids:
            vals[id] = {
                "num_targets": 0,
                "num_emails_verified": 0,
                "num_emails_error": 0,
            }
        for r in res:
            vals[r.list_id]["num_targets"] = r.count
        res = db.query(
            "SELECT list_id,count(*) FROM mkt_target WHERE list_id IN %s AND email_status='verified' GROUP BY list_id", tuple(ids))
        for r in res:
            vals[r.list_id]["num_emails_verified"] = r.count
        res = db.query(
            "SELECT list_id,count(*) FROM mkt_target WHERE list_id IN %s AND email_status IN ('error_syntax','error_dns','error_smtp') GROUP BY list_id", tuple(ids))
        for r in res:
            vals[r.list_id]["num_emails_error"] = r.count
        return vals

    def remove_duplicate_emails(self, ids, context={}):
        obj = self.browse(ids[0])
        last_email = None
        del_ids = []
        for target in get_model("mkt.target").search_browse([["list_id", "=", obj.id]], order="email,id"):
            if last_email and target.email == last_email:
                del_ids.append(target.id)
            else:
                last_email = target.email
        get_model("mkt.target").delete(del_ids)
        return {
            "flash": "%d targets deleted" % len(del_ids),
        }

    def verify_emails(self, ids, context={}):
        obj = self.browse(ids[0])
        i = 0
        domain_cache = {}
        last_smtp_host = None
        last_smtp_time = None
        for target in get_model("mkt.target").search_browse([["list_id", "=", obj.id]], order="email,id"):
            i += 1
            if target.email_status == "verified":
                continue
            print("verifying email %s (%d)" % (target.email, i))
            try:
                email_status = "error_syntax"
                if not utils.check_email_syntax(target.email):
                    raise Exception("Invalid email syntax")
                email_status = "error_dns"
                domain = utils.get_email_domain(target.email)
                if domain in domain_cache:
                    mx_records = domain_cache[domain]
                else:
                    mx_records = utils.get_mx_records(domain)
                    domain_cache[domain] = mx_records
                if not mx_records:
                    raise Exception("MX record not found")
                email_status = "error_smtp"
                host = mx_records[0][1]
                if last_smtp_host and last_smtp_time and host == last_smtp_host and time.time() - last_smtp_time < 5:
                    print("sleeping before connecting again to %s..." % host)
                    time.sleep(5)
                last_smtp_host = host
                last_smtp_time = time.time()
                serv = smtplib.SMTP(timeout=15)
                try:
                    serv.connect(host)
                except:
                    raise Exception("Failed to connect to SMTP server")
                status, _ = serv.helo()
                if status != 250:
                    serv.quit()
                    raise Exception("Invalid SMTP HELO response code: %s" % status)
                serv.mail("")
                status, _ = serv.rcpt(target.email)
                if status != 250:
                    serv.quit()
                    raise Exception("Invalid SMTP RCPT response code: %s" % status)
                serv.quit()
                email_status = "verified"
                email_error = None
            except Exception as e:
                email_error = str(e)
                import traceback
                traceback.print_exc()
            finally:
                target.write({"email_status": email_status, "email_error": email_error})
                db = database.get_connection()
                db.commit()

TargetList.register()
