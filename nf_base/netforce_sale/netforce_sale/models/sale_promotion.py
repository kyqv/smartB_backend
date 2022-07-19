from netforce.model import Model,fields,get_model
from netforce.database import get_connection
from netforce import access
from datetime import *
import time

class Promotion(Model):
    _name="sale.promotion"
    _string="Promotion"
    _fields={
        "name": fields.Char("Promotion Title",required=True),
        "code": fields.Char("Promotion Code"), # XXX: deprecated
        "date_from": fields.Date("From Date",search=True),
        "date_to": fields.Date("To Date"),
        "buy_prod_groups": fields.Many2Many("product.group","Apply To Product Groups",reltable="m2m_promotion_buy_groups",relfield="promotion_id",relfield_other="group_id"),
        "buy_products": fields.Many2Many("product","Apply To Products",reltable="m2m_promotion_buy_products",relfield="promotion_id",relfield_other="product_id"),
        "buy_min_amount": fields.Integer("Minimum Order Amount"),
        "buy_min_qty": fields.Integer("Minimum Order Qty"),
        "apply_multi": fields.Boolean("Allow multiple use per order"),
        "discount_products": fields.Many2Many("product","Discount Products",reltable="m2m_promotion_discount_products",relfield="promotion_id",relfield_other="product_id"),
        "discount_prod_groups": fields.Many2Many("product.group","Discount Product Groups",reltable="m2m_promotion_discount_groups",relfield="promotion_id",relfield_other="group_id"),
        "related_products": fields.Many2Many("product","Related Products",reltable="m2m_promotion_related_products",relfield="promotion_id",relfield_other="product_id"),
        "related_prod_groups": fields.Many2Many("product.group","Related Product Groups",reltable="m2m_promotion_related_groups",relfield="promotion_id",relfield_other="group_id"),
        "discount_percent_item": fields.Decimal("Discount Percent Per Item"),
        "discount_amount_item": fields.Decimal("Discount Amount Per Item"),
        "discount_percent_order": fields.Decimal("Discount Percent Per Order"),
        "discount_amount_order": fields.Decimal("Discount Amount Per Order"),
        "discount_max_qty": fields.Integer("Discount Item Max Qty"),
        "product_id": fields.Many2One("product","Promotion Product"),
        "contact_categs": fields.Many2Many("contact.categ","Customer Categories"),
        "contact_groups": fields.Many2Many("contact.group","Customer Groups"),
        "state": fields.Selection([["active","Active"],["inactive","Inactive"]],"Status",required=True),
        "company_id": fields.Many2One("company","Company"),
        "cart_offer_message": fields.Text("Add discounted product"),
        "cart_confirm_message": fields.Text("Offer taken"),
        "can_apply": fields.Boolean("Can Apply",function="_can_apply"),
        "is_applied": fields.Boolean("Is Applied",function="_is_applied"),
        "coupon_master_id": fields.Many2One("sale.coupon.master","Require Coupon"),
        "max_uses_per_customer": fields.Integer("Max Uses Per Customer"),
        "max_total_uses": fields.Integer("Max Total Uses"),
        "description": fields.Text("Description"),
        "auto_apply": fields.Boolean("Auto Apply Promotion"),
    }
    _defaults={
        "state": "active",
        "company_id": lambda *a: access.get_active_company(),
    }
    _order="id desc"

    def activate(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state":"active"})

    def deactivate(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state":"inactive"})

    def _can_apply(self,ids,context={}):
        print("promotion.can_apply",ids)
        cart_id=context.get("cart_id")
        print("cart_id=%s"%cart_id)
        vals={}
        for prom_id in ids:
            if cart_id and get_model("ecom.cart").can_apply_promotion([cart_id],prom_id):
                vals[prom_id]=True
            else:
                vals[prom_id]=False
        return vals

    def _is_applied(self,ids,context={}):
        print("promotion.is_applied",ids)
        cart_id=context.get("cart_id")
        print("cart_id=%s"%cart_id)
        vals={}
        for prom_id in ids:
            if cart_id and get_model("ecom.cart").is_promotion_applied([cart_id],prom_id):
                vals[prom_id]=True
            else:
                vals[prom_id]=False
        print("vals",vals)
        return vals

Promotion.register()
