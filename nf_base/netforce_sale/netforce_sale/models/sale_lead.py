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
from netforce import utils
from datetime import *
import time
from netforce import access
from email.utils import parseaddr


class Lead(Model):
    _name = "sale.lead"
    _string = "Lead"
    _audit_log = True
    _multi_company = True
    _name_field="title"
    _key = ["number"]
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "user_id": fields.Many2One("base.user", "Lead Owner"),
        "first_name": fields.Char("First Name", search=True),
        "last_name": fields.Char("Last Name", search=True),
        "contact_name": fields.Char("Contact Name", search=True, required=True),
        "name": fields.Char("Name", function="get_name"),
        "company": fields.Char("Company", search=True),
        "title": fields.Char("Title", required=True, search=True),
        "state": fields.Selection([["new", "New"], ["converted", "Converted"], ["referred","Referred"], ["voided", "Voided"]], "Status", required=True),
        "phone": fields.Char("Phone", search=True),
        "email": fields.Char("Email", search=True),
        "rating": fields.Selection([["hot", "Hot"], ["warm", "Warm"], ["cold", "Cold"]], "Rating"), # XXX: deprecated
        "street": fields.Char("Street"),
        "city": fields.Char("City"),
        "province": fields.Char("State/Province"),
        "zip": fields.Char("Zip/Postal Code"),
        "country_id": fields.Many2One("country", "Country"),
        "website": fields.Char("Website"),
        "employees": fields.Char("No. of Employees"),
        "revenue": fields.Char("Annual Revenue"),
        "lead_source": fields.Char("Lead Source"), # XXX: deprecated
        "source_id": fields.Many2One("lead.source","Lead Source", search=True),
        "industry": fields.Char("Industry", search=True),
        "description": fields.Text("Description"),
        "assigned_id": fields.Many2One("base.user", "Assigned To"),
        "date": fields.Date("Date", search=True, required=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "activities": fields.One2Many("sale.activ", "related_id", "Activities"),
        "addresses": fields.One2Many("address", "lead_id", "Addresses"),
        "company_id": fields.Many2One("company", "Company"),
        "emails": fields.One2Many("email.message", "related_id", "Emails"),
        "year": fields.Char("Year", sql_function=["year", "date"]),
        "quarter": fields.Char("Quarter", sql_function=["quarter", "date"]),
        "month": fields.Char("Month", sql_function=["month", "date"]),
        "week": fields.Char("Week", sql_function=["week", "date"]),
        "sale_opports": fields.One2Many("sale.opportunity","lead_id","Sales Opportunities"),
        "age_days": fields.Integer("Age (Days)",function="get_age_days"),
        "refer_contact_id": fields.Many2One("contact","Referred To"),
        "refer_reason_id": fields.Many2One("reason.code","Refer Reason",condition=[["type","=","lead_refer"]]),
        "documents": fields.One2Many("document", "related_id", "Documents"),
    }

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="sale_lead",context=context)
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            if not num:
                return None
            user_id = access.get_active_user()
            company_id = access.get_active_company()
            access.set_active_user(1)
            access.set_active_company(1)
            res = self.search([["number", "=", num]])
            access.set_active_user(user_id)
            access.set_active_company(company_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    _defaults = {
        "number": _get_number,
        "state": "new",
        "active": True,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "company_id": lambda *a: access.get_active_company(),
    }
    _order="date desc,id desc"

    def copy_to_contact(self, ids, context={}):
        obj = self.browse(ids)[0]
        messages = []
        if obj.company:
            res = get_model("contact").search([["name", "=", obj.company]])
            if res:
                comp_contact_id = res[0]
                messages.append("Contact already exists for %s." % obj.company)
            else:
                vals = {
                    "type": "org",
                    "name": obj.company,
                    "phone": obj.phone,
                    "website": obj.website,
                    "industry": obj.industry,
                    "employees": obj.employees,
                    "revenue": obj.revenue,
                    "customer": True,
                }
                comp_contact_id = get_model("contact").create(vals, context=context)
                messages.append("Contact created for %s." % obj.company)
        else:
            comp_contact_id = None

        if obj.first_name:
            name = obj.first_name + " " + obj.last_name
        else:
            name = obj.last_name
        res = get_model("contact").search([["name", "=", name]])
        if res:
            contact_id = res[0]
            messages.append("Contact already exists for %s." % name)
        else:
            vals = {
                "type": "person",
                "first_name": obj.first_name,
                "last_name": obj.last_name,
                "contact_id": comp_contact_id,
                "title": obj.title,
                "phone": obj.phone,
                "email": obj.email,
            }
            # TODO: copy address
            contact_id = get_model("contact").create(vals, context=context)
            messages.append("Contact created for %s." % name)
        return {
            "next": {
                "name": "contact",
                "mode": "form",
                "active_id": contact_id,
            },
            "flash": "\n".join(messages),
        }

    def void(self,ids,context={}):
        n=0
        for obj in self.browse(ids):
            obj.write({"state": "voided"})
            n+=1
        return {
            "flash": "%d sales leads voided"%n,
        }

    def set_new(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state": "new"})

    def copy_to_opport(self,ids,context={}):
        n=0
        for obj in self.browse(ids):
            email=obj.email
            if not email:
                raise Exception("Missing email")
            res=get_model("contact").search([["email","=",email]])
            if res:
                contact_id=res[0]
            else:
                vals={
                    "type": "person",
                    "last_name": obj.contact_name,
                    "email": email,
                }
                contact_id=get_model("contact").create(vals)
            vals = {
                "number": obj.number,
                "lead_id": obj.id,
                "user_id": obj.user_id.id,
                "name": obj.title,
                "contact_id": contact_id,
                "source_id": obj.source_id.id,
                "company_id": obj.company_id.id,
            }
            opport_id = get_model("sale.opportunity").create(vals)
            for email in obj.emails:
                vals={
                    "name_id": "contact,%s"%contact_id,
                    "related_id": "sale.opportunity,%s"%opport_id,
                }
                email.write(vals)
            for doc in obj.documents:
                vals={
                    "related_id": "sale.opportunity,%s"%opport_id,
                }
                doc.write(vals)
            obj.write({"state": "converted"})
            n+=1
        return {
            "flash": "%d sales opportunities created"%n,
        }

    def send_reminders(self,template=None,min_days=None,company=None,to_addrs=None,context={}):
        print("SaleLead.send_reminders",template)
        objs=[]
        cond=[["state","=","new"]]
        if company:
            cond.append(["company_id.code","=",company])
        for obj in self.search_browse(cond):
            if min_days and obj.age_days<min_days:
                continue
            objs.append(obj)
        if objs:
            if not template:
                raise Exception("Missing template")
            res=get_model("email.template").search([["name","=",template]])
            if not res:
                raise Exception("Template not found: %s"%template)
            tmpl_id=res[0]
            data={
                "objs": objs,
                "num_objs": len(objs),
                "to_addrs": to_addrs,
            }
            print("data",data)
            get_model("email.template").create_email([tmpl_id],data=data)
            get_model("email.message").send_emails_async()
        return "%d leads reminded"%len(objs)

    def get_age_days(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            days=None
            today=datetime.today().date()
            d=datetime.strptime(obj.date,"%Y-%m-%d").date()
            n=0
            while d<today:
                d+=timedelta(days=1)
                if d.weekday() not in (5,6):
                    n+=1
            days=n
            vals[obj.id]=days
        return vals

    def check_spam(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.emails and obj.emails[0].is_spam:
                obj.void()

    def refer(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.refer_reason_id:
            raise Exception("Missing refer reason")
        obj.write({"state":"referred"})
        obj.trigger("refer")

    def forward_email_old(self,from_addr=None,to_addrs=None,context={}):
        trigger_ids = context.get("trigger_ids")
        if trigger_ids is None:
            raise Exception("Missing trigger ids")
        obj=self.browse(trigger_ids[0])
        if not obj.emails:
            raise Exception("No emails for lead %s"%obj.number)
        subject="[%s] %s"%(obj.number,obj.title)
        vals={
            "from_addr": from_addr or obj.email,
            "reply_to": obj.email,
            "to_addrs": to_addrs or obj.user_id.email,
            "subject": subject,
            "body": obj.description,
            "state": "to_send",
            "related_id": "sale.lead,%d"%obj.id,
        }
        if not vals["to_addrs"]:
            raise Exception("Missing email address to forward lead %s"%obj.number)
        if vals["from_addr"]!=obj.email:
            vals["reply_to"]=obj.email
        email_id=get_model("email.message").create(vals)
        get_model("email.message").send_emails_async()

    def forward_email(self,from_addr=None,to_addrs=None,context={}):
        trigger_ids = context.get("trigger_ids")
        if trigger_ids is None:
            raise Exception("Missing trigger ids")
        obj=self.browse(trigger_ids[0])
        found_email=None
        for email in obj.emails:
            if email.state!="received":
                continue
            found_email=email
        if not found_email:
            raise Exception("Lead email not found")
        subject="[%s] %s"%(obj.number,obj.title)
        if not to_addrs:
            raise Exception("Missing email address to forward lead %s"%obj.number)
        vals={
            "from_addr": from_addr or obj.email,
            "reply_to": obj.email,
            "to_addrs": to_addrs or obj.user_id.email,
            "subject": subject,
        }
        email_id=found_email.forward_email(vals)
        get_model("email.message").write([email_id],{"state":"to_send"})
        get_model("email.message").send_emails_async()

Lead.register()
