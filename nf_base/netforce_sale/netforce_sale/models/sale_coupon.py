from netforce.model import Model,fields,get_model
from datetime import *
import random

class Coupon(Model):
    _name="sale.coupon"
    _string="Coupon"
    _key=["code"]
    _fields={
        "master_id": fields.Many2One("sale.coupon.master","Coupon Master",required=True,search=True),
        "code": fields.Char("Code",required=True),
        "contact_id": fields.Many2One("contact","Customer",required=True,search=True),
        "state": fields.Selection([["available","Available"],["in_use","In Use"],["used","Used"],["expired","Expired"]],"Status",required=True,search=True),
        "active": fields.Boolean("Active",required=True),
        "use_date": fields.DateTime("Usage Date",readonly=True),
        "expiry_date": fields.DateTime("Expiry Date"),
        "use_duration": fields.Integer("Usability Duration (minutes)"),
        "hide_date": fields.DateTime("Hide Date"),
        "contact_email": fields.Char("Contact Email", function="_get_related", function_search="_search_related", function_context={"path": "contact_id.email"}, search=True),
    }

    def _get_code(self, context={}):
        while 1:
            code = "%.3d"%random.randint(0,999)
            code += "-"
            code += "%.3d"%random.randint(0,999)
            code += "-"
            code += "%.4d"%random.randint(0,9999)
            if not get_model("sale.coupon").search([["code","=",code]]):
                return code

    _defaults={
        "state": "available",
        "active": True,
        "code": _get_code,
    }
    _order="id desc"

    def use_coupon(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.state!="available":
            raise Exception("Invalid coupon status")
        t=datetime.now()
        if obj.expiry_date and t.strftime("%Y-%m-%d %H:%M:%S")>=obj.expiry_date:
            raise Exception("Coupon is expired")
        vals={
            "state": "in_use",
            "use_date": t.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if obj.use_duration:
            t2=t+timedelta(minutes=obj.use_duration)
            vals["expiry_date"]=t2.strftime("%Y-%m-%d %H:%M:%S")
        obj.write(vals)

    def update_coupons(self,context={}):
        t=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ids=self.search([["state","=","available"],["expiry_date","<=",t]])
        if ids:
            self.write(ids,{"state":"expired"})
        ids=self.search([["state","=","in_use"],["expiry_date","<=",t]])
        if ids:
            self.write(ids,{"state":"used"})
        ids=self.search([["active","=",True],["hide_date","<=",t]])
        if ids:
            self.write(ids,{"active":False})

    #def get_report_data(self,ids,context={}):
        #objs = self.browse(ids)
        #for obj in objs:
            #if obj.state == "available":
                #t=datetime.now()
                #vals={
                    #"state": "used",
                    #"use_date": t.strftime("%Y-%m-%d %H:%M:%S"),
                    #"expiry_date": t.strftime("%Y-%m-%d %H:%M:%S"),
                #}
                #obj.write(vals)
        #data = super().get_report_data(ids, context)
        #return data
        
    def create_individual_coupon(self, master_ids=[], context={}):
        contact_ids = context.get("trigger_ids")
        for contact_id in contact_ids:
            for master_id in master_ids:
                master = get_model("sale.coupon.master").browse(master_id)
                vals = {
                    "master_id": master_id,
                    "contact_id": contact_id,
                    "expiry_date": master.expiry_date,
                    "use_duration": master.use_duration,
                    "hide_date": master.hide_date,
                }
                self.create(vals)

Coupon.register()
