from netforce.model import Model,fields,get_model
from datetime import *
import random
import string

class CouponMaster(Model):
    _name="sale.coupon.master"
    _string="Coupon Master"
    _fields={
        "name": fields.Char("Coupon Name",required=True),
        "banner_image": fields.File("Coupon Banner Image"),
        "image": fields.File("Coupon Image"),
        "description": fields.Text("Description"),
        "instructions": fields.Text("Instructions"),
        "notes": fields.Text("Notes"),
        "use_duration": fields.Integer("Usability Duration (minutes)"),
        "expiry_date": fields.DateTime("Expiry Date"),
        "hide_date": fields.DateTime("Hide Date"),
        "contact_categs": fields.Many2Many("contact.categ","Customer Categories"),
        "contact_groups": fields.Many2Many("contact.group","Customer Groups"),
        "active": fields.Boolean("Active",required=True),
        "coupons": fields.One2Many("sale.coupon","master_id","Coupons"),
        "promotions": fields.One2Many("sale.promotion","coupon_master_id","Promotions"),
    }
    _defaults={
        "state": "available",
        "active": True,
    }
    _order="name"

    def create_coupons(self,ids,context={}):
        obj=self.browse(ids[0])
        cond=[]
        if obj.contact_categs:
            categ_ids=[]
            for categ in obj.contact_categs:
                sub_categ_ids=get_model("contact.categ").search([["id","child_of",categ.id]])
                categ_ids+=sub_categ_ids
            categ_ids=list(set(categ_ids))
            cond.append([["categ_id","in",categ_ids]])
        if obj.contact_groups:
            group_ids=[l.id for l in obj.contact_groups]
            cond.append([["groups.id","in",group_ids]])
        if not cond:
            raise Exception("Missing customer category or groups")
        contact_ids=get_model("contact").search(cond)
        if not contact_ids:
            raise Exception("No contact matches criteria")
        count=0
        for contact_id in contact_ids:
            vals={
                "master_id": obj.id,
                "contact_id": contact_id,
                "expiry_date": obj.expiry_date,
                "use_duration": obj.use_duration,
                "hide_date": obj.hide_date,
            }
            get_model("sale.coupon").create(vals)
            count+=1
        return {
            "flash": "%d coupons created"%count,
        }

CouponMaster.register()
