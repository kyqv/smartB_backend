from netforce.model import Model, fields, get_model
from email.utils import parseaddr, parsedate_tz, formatdate, getaddresses
import re


class EmailMessage(Model):
    _inherit = "email.message"

    def link_emails(self,ids,context={}):
        print("EmailMessage.link_emails",ids)
        super().link_emails(ids,context=context)
        for obj in self.browse(ids):
            lead_id=None
            opport_id=None
            m=re.search("\[(.*?)\]",obj.subject)
            if m:
                number=m.group(1)
                res=get_model("sale.lead").search([["number","=",number]])
                if res:
                    lead_id=res[0]
                res=get_model("sale.opportunity").search([["number","=",number]])
                if res:
                    opport_id=res[0]
            if not lead_id and not opport_id:
                continue
            if opport_id:
                opport=get_model("sale.opportunity").browse(opport_id)
                obj.write({"related_id":"sale.opportunity,%s"%opport.id,"name_id":"contact,%s"%opport.contact_id.id})
            elif lead_id:
                lead=get_model("sale.lead").browse(lead_id)
                obj.write({"related_id":"sale.lead,%s"%lead_id})

    def copy_to_lead(self,user=None,from_sales=False,lead_source=None,company_code=None,context={}):
        print("EmailMessage.copy_to_lead")
        trigger_ids = context.get("trigger_ids")
        if trigger_ids is None:
            raise Exception("Missing trigger ids")
        print("trigger_ids",trigger_ids)
        for obj in self.browse(trigger_ids):
            if obj.related_id:
                return
            from_name,from_email=parseaddr(obj.from_addr)
            if from_sales:
                try:
                    orig_from_name,orig_from_email=parseaddr(obj.orig_from_addr)
                    if orig_from_email:
                        from_name=orig_from_name
                        from_email=orig_from_email
                except:
                    pass
            if company_code:
                res=get_model("company").search([["code","=",company_code]])
                if not res:
                    raise Exception("Company not found: %s"%company_code)
                company_id=res[0]
            else:
                company_id=None
            vals={
                "date": obj.date[:10],
                "title": obj.subject,
                "contact_name": from_name or from_email,
                "email": from_email,
                "description": obj.body,
                "company_id": company_id,
            }
            if user:
                res=get_model("base.user").search([["login","=",user]])
                if not res:
                    raise Exception("User not found: %s"%user)
                vals["user_id"]=res[0]
            if lead_source:
                res=get_model("lead.source").search([["name","=",lead_source]])
                if not res:
                    raise Exception("Lead source not found: %s"%lead_source)
                lead_source_id=res[0]
                vals["source_id"]=lead_source_id
            lead_id=get_model("sale.lead").create(vals)
            obj.write({
                "related_id": "sale.lead,%s"%lead_id,
            })
            get_model("sale.lead").trigger([lead_id],"new_lead_from_email")

    def convert_lead(self,lead_source=None,context={}):
        print("EmailMessage.convert_lead")
        trigger_ids = context.get("trigger_ids")
        if trigger_ids is None:
            raise Exception("Missing trigger ids")
        print("trigger_ids",trigger_ids)
        for obj in self.browse(trigger_ids):
            if not obj.related_id or obj.related_id._model!="sale.lead":
                continue
            lead=obj.related_id
            if lead.state=="new":
                lead.copy_to_opport()

EmailMessage.register()
