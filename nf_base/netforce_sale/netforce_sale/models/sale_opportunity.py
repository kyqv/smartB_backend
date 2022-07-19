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
from datetime import *
import time
from netforce.access import get_active_company,get_active_user,set_active_user
from email.utils import parseaddr
from netforce import access


class Opportunity(Model):
    _name = "sale.opportunity"
    _string = "Opportunity"
    _audit_log = True
    #_key = ["company_id", "number"] # XXX
    _multi_company = True
    _name_field="number"
    _content_search=True
    _fields = {
        "number": fields.Char("Number", required=True, search=True),
        "user_id": fields.Many2One("base.user", "Opportunity Owner"),
        "name": fields.Char("Opportunity Name", required=True, search=True),
        "contact_id": fields.Many2One("contact", "Contact", required=True, search=True),
        "campaign_id": fields.Many2One("mkt.campaign", "Marketing Campaign"),
        "date": fields.Date("Open Date", search=True,required=True),
        "date_close": fields.Date("Close Date", search=True),
        "stage_id": fields.Many2One("sale.stage", "Stage", search=True),
        "probability": fields.Decimal("Probability (%)"),
        "amount": fields.Decimal("Amount", search=True),
        "lead_source": fields.Char("Lead Source", search=True), # XXX: deprecated
        "source_id": fields.Many2One("lead.source","Lead Source"),
        "lead_id": fields.Many2One("sale.lead","Sales Lead"),
        "next_step": fields.Char("Next Step"),
        "description": fields.Text("Description"),
        "state": fields.Selection([["open", "Open"], ["won", "Won"], ["lost", "Lost"], ["paused","Paused"], ["canceled","Canceled"]], "Status"),
        "product_id": fields.Many2One("product", "Product"),
        "products": fields.Many2Many("product", "Products"),
        "qty": fields.Decimal("Qty"),
        "quotations": fields.One2Many("sale.quot", "opport_id", "Quotations"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "activities": fields.One2Many("sale.activ", "related_id", "Activities"),
        "emails": fields.One2Many("email.message", "related_id", "Emails"),
        "competitors": fields.One2Many("opport.compet", "opport_id", "Competitors"),
        "company_id": fields.Many2One("company", "Company"),
        "region_id": fields.Many2One("region", "Region", search=True),
        "industry_id": fields.Many2One("industry", "Industry", search=True),
        "year": fields.Char("Year", sql_function=["year", "date_close"]),
        "quarter": fields.Char("Quarter", sql_function=["quarter", "date_close"]),
        "month": fields.Char("Month", sql_function=["month", "date_close"]),
        "week": fields.Char("Week", sql_function=["week", "date_close"]),
        "agg_amount": fields.Decimal("Total Amount", agg_function=["sum", "amount"]),
        "documents": fields.One2Many("document", "related_id", "Documents"),
        "categ_id": fields.Many2One("sale.categ","Sales Category"),
        "last_email_days": fields.Integer("Days Since Last Email",function="get_last_email_days"),
        "lost_reason_id": fields.Many2One("reason.code","Lost Reason",condition=[["type","=","lost_sale_opport"]]),
        "cancel_reason_id": fields.Many2One("reason.code","Cancel Reason",condition=[["type","=","cancel_sale_opport"]]),
        "lead_id": fields.Many2One("sale.lead","Sales Lead"),
        "email_body": fields.Text("Email Body",function="get_email_body"),
        "age_days": fields.Integer("Age (Days)",function="get_age"),
        "date_week": fields.Char("Week",function="get_date_agg",function_multi=True),
        "date_month": fields.Char("Month",function="get_date_agg",function_multi=True),
        "remind_date": fields.Date("Next Reminder Date"),
        "notifs": fields.One2Many("notif","related_id","Notifications"),
    }

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="sale_opport",context=context)
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            if not num:
                return None
            user_id = get_active_user()
            set_active_user(1)
            res = self.search([["number", "=", num]])
            set_active_user(user_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    _defaults = {
        "state": "open",
        "user_id": lambda *a: get_active_user(),
        "company_id": lambda *a: get_active_company(),
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "number": _get_number,
    }
    _order = "date desc,id desc"

    def name_get(self, ids, context={}):
        vals = []
        for obj in self.browse(ids):
            name = "[%s] %s" % (obj.number, obj.name)
            vals.append((obj.id, name))
        return vals

    def copy_to_quotation(self, ids, context):
        id = ids[0]
        obj = self.browse(id)
        template_id=context.get("template_id")
        if template_id:
            quot_id=get_model("sale.quot").copy([template_id])["new_id"]
            vals={
                "opport_id": obj.id,
                "ref": obj.number,
                "contact_id": obj.contact_id.id,
                "user_id": obj.user_id.id,
            }
            get_model("sale.quot").write([quot_id],vals)
        else:
            vals = {
                "opport_id": obj.id,
                "ref": obj.number,
                "contact_id": obj.contact_id.id,
                "lines": [],
                "user_id": obj.user_id.id,
            }
            prod = obj.product_id
            if prod:
                line_vals = {
                    "product_id": prod.id,
                    "description": prod.name_get()[0][1],
                    "qty": obj.qty or 1,
                    "uom_id": prod.uom_id.id,
                    "unit_price": obj.amount or prod.sale_price,
                }
                vals["lines"].append(("create", line_vals))
            quot_id = get_model("sale.quot").create(vals, context=context)
        quot = get_model("sale.quot").browse(quot_id)
        return {
            "next": {
                "name": "quot",
                "mode": "form",
                "active_id": quot_id,
            },
            "flash": "Quotation %s created from opportunity" % quot.number
        }

    def copy(self, ids, context):
        obj = self.browse(ids)[0]
        vals = {
            "user_id": obj.user_id.id,
            "name": obj.name,
            "contact_id": obj.contact_id.id,
            "contact_id": obj.contact_id.id,
            "date_close": obj.date_close,
            "stage_id": obj.stage_id.id,
            "probability": obj.probability,
            "amount": obj.amount,
            "lead_source": obj.lead_source,
            "product_id": obj.product_id.id,
            "next_step": obj.next_step,
            "description": obj.description,
        }
        new_id = self.create(vals, context=context)
        new_obj = self.browse(new_id)
        return {
            "next": {
                "name": "opport_edit",
                "active_id": new_id,
            },
            "flash": "Opportunity copied",
        }

    def copy_from_email(self,user_login=None,context={}):
        print("@"*80)
        print("SaleOpport.copy_from_email")
        trigger_ids=context["trigger_ids"]
        email_id=trigger_ids[0]
        email=get_model("email.message").browse(email_id)
        parent_id=None
        if email.parent_uid:
            res=get_model("email.message").search([["message_id","=",email.parent_uid]])
            if res:
                parent_id=res[0]
        if parent_id:
            parent=get_model("email.message").browse(parent_id)
            name_id="%s,%d"%(parent.name_id._model,parent.name_id.id) if parent.name_id else None
            related_id="%s,%d"%(parent.related_id._model,parent.related_id.id) if parent.related_id else None
            email.write({
                "name_id": name_id,
                "related_id": related_id,
            })
        else:
            if email.orig_from_addr:
                from_name,from_email=parseaddr(email.orig_from_addr)
            else:
                from_name,from_email=parseaddr(email.from_addr)
            res=get_model("contact").search([["email","=",from_email]])
            if res:
                contact_id=res[0]
            else:
                vals={
                    "type": "person",
                    "last_name": from_name or from_email,
                    "email": from_email,
                }
                contact_id=get_model("contact").create(vals)
            if user_login:
                res=get_model("base.user").search([["login","=",user_login]])
                user_id=res[0] if res else None
            else:
                user_id=None
            vals={
                "name": email.subject,
                "contact_id": contact_id,
                "date": email.date[:10],
                "user_id": user_id,
            }
            opport_id=self.create(vals)
            email.write({
                "name_id": "contact,%s"%contact_id,
                "related_id": "sale.opportunity,%s"%opport_id,
            })

    def get_last_email_days(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            days=None
            if obj.emails:
                email=obj.emails[0]
                today=datetime.today().date()
                d=datetime.strptime(email.date,"%Y-%m-%d %H:%M:%S").date()
                n=0
                while d<today:
                    d+=timedelta(days=1)
                    if d.weekday() not in (5,6):
                        n+=1
                days=n
            vals[obj.id]=days
        return vals

    def send_reminders(self,min_days=None,template=None,company=None,to_addrs=None,context={}):
        objs=[]
        cond=[["state","=","open"]]
        if company:
            cond.append(["company_id.code","=",company])
        for obj in self.search_browse(cond):
            if min_days and (not obj.last_email_days or obj.last_email_days<min_days):
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
            get_model("email.template").create_email([tmpl_id],data=data)
            get_model("email.message").send_emails_async()
        return "%d opportunities reminded"%len(objs)

    def won(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state": "won"})

    def lost(self,ids,context={}):
        for obj in self.browse(ids):
            if not obj.lost_reason_id:
                raise Exception("Missing lost reason")
            obj.write({"state": "lost"})

    def pause(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state": "paused"})

    def cancel(self,ids,context={}):
        for obj in self.browse(ids):
            if not obj.cancel_reason_id:
                raise Exception("Missing cancel reason")
            obj.write({"state": "canceled"})

    def reopen(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state": "open"})

    def get_email_body(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            body=None
            if obj.emails:
                body=obj.emails[0].body
            vals[obj.id]=body
        return vals

    def get_age(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=(datetime.today()-datetime.strptime(obj.date[:10],"%Y-%m-%d")).days if obj.date else None
        return vals

    def get_date_agg(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.date:
                d=datetime.strptime(obj.date,"%Y-%m-%d")
                month=d.strftime("%Y-%m")
                week=d.strftime("%Y-W%W")
            else:
                week=None
                month=None
            vals[obj.id]={
                "date_week": week,
                "date_month": month,
            }
        return vals

    def write(self,ids,vals,context={}):
        super().write(ids,vals,context=context)
        if "remind_date" in vals:
            for obj in self.browse(ids):
                obj.update_notifs()

    def update_notifs(self,ids,context={}):
        access.set_active_user(1)
        obj=self.browse(ids[0])
        for notif in obj.notifs:
            if notif.state=="new":
                notif.delete()
        if not obj.remind_date:
            return
        vals={
            "user_id": obj.user_id.id,
            "time": obj.remind_date,
            "title": "Please follow up opportunity %s"%obj.number,
            "related_id": "sale.opportunity,%s"%obj.id,
        }
        notif_id=get_model("notif").create(vals)

Opportunity.register()
