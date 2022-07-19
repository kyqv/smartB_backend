from netforce.model import Model,fields,get_model
from netforce.utils import *
import time

class Voucher(Model):
    _name="sale.voucher"
    _string="Voucher"
    _name_field="code"
    _fields={
        "code": fields.Char("Voucher Code",required=True,search=True),
        "sequence": fields.Char("Sequence"),
        "benefit_type": fields.Selection([["fixed_discount_order","Fixed Discount On Order"],["free_product","Free Product"],["percent_discount_product","Percent Discount On Product"],["credit","Credits"]],"Benefit For Customer",required=True),
        "refer_benefit_type": fields.Selection([["credit","Credits"]],"Benefit For Referring Customer"),
        "discount_amount": fields.Decimal("Discount Amount"),
        "discount_percent": fields.Decimal("Discount Percent"),
        "discount_product_groups": fields.Many2Many("product.group","Discount Product Groups",reltable="m2m_voucher_discount_product_groups",relfield="voucher_id",relfield_other="product_group_id"),
        "discount_product_id": fields.Many2One("product","Discount Product"),
        "discount_max_qty": fields.Integer("Discount Max Qty"),
        "credit_amount": fields.Decimal("Credit Amount"),
        "refer_credit_amount": fields.Decimal("Credit Amount For Referring Customer"),
        "min_order_amount": fields.Decimal("Min Order Amount"),
        "min_order_amount_msg": fields.Text("Error Message"),
        "state": fields.Selection([["active","Active"],["inactive","Inactive"]],"Status",required=True),
        "max_orders_per_customer": fields.Integer("Max Orders Per Customer"),
        "max_orders_per_customer_msg": fields.Text("Error Message"),
        "max_orders": fields.Integer("Max Orders Total"),
        "max_orders_msg": fields.Text("Error Message"),
        "new_customer": fields.Boolean("New Customers Only"),
        "new_customer_msg": fields.Text("Error Message"),
        "contact_groups": fields.Many2Many("contact.group","Customer Groups"),
        "contact_groups_msg": fields.Text("Error Message"),
        "product_groups": fields.Many2Many("product.group","Critera Product Groups"), # XXX: rename
        "product_groups_msg": fields.Text("Error Message"),
        "cond_product_id": fields.Many2One("product","Criteria Product"),
        "cond_product_msg": fields.Text("Error Message"),
        "cond_product_categ_id": fields.Many2One("product.categ","Criteria Product Category"),
        "cond_product_categ_msg": fields.Text("Error Message"),
        "min_qty": fields.Decimal("Min Qty"),
        "min_qty_msg": fields.Text("Error Message"),
        "qty_multiple": fields.Decimal("Qty Multiple"),
        "qty_multiple_msg": fields.Text("Error Message"),
        "customer_id": fields.Many2One("contact","Customer"),
        "customer_msg": fields.Text("Error Message"),
        "description": fields.Text("Description"),
        "expire_date": fields.Date("Expiration Date"),
        "expire_date_msg": fields.Text("Error Message"),
        "carts": fields.One2Many("ecom2.cart","voucher_id","Carts"),
        "sale_orders": fields.One2Many("sale.order","voucher_id","Sales Orders"),
        "product_id": fields.Many2One("product","Configuration Product",required=True),
    }
    _defaults={
        "state": "active",
    }
    _order="sequence,code"

    def apply_voucher(self,ids,context={}):
        print("$"*80)
        print("voucher.apply_coupon",ids)
        obj=self.browse(ids[0])
        contact_id=context.get("contact_id")
        print("contact_id",contact_id)
        amount_total=context.get("amount_total")
        print("amount_total",amount_total)
        amount_ship=context.get("amount_ship")
        print("amount_ship",amount_ship)
        amount_total_ship=(amount_total or 0)+(amount_ship or 0)
        products=context.get("products",[])
        print("products",products)
        order_type=context.get("order_type",None)
        date=time.strftime("%Y-%m-%d")
        try:
            if obj.expire_date and date>obj.expire_date:
                msg="This voucher is expired."
                if obj.expire_date_msg:
                    msg=obj.expire_date_msg
                raise NFException(msg)
            if obj.customer_id and contact_id!=obj.customer_id.id:
                msg="This voucher can not apply to this customer." ###FIX ME / should be set to inactive .
                if obj.customer_msg:
                    msg=obj.customer_msg
                raise NFException(msg)
            if obj.cond_order_type:
                if order_type!=obj.cond_order_type:
                    msg="Wrong order type"
                    if obj.cond_order_type_msg:
                        msg=obj.cond_order_type_msg
                    raise NFException(msg)
            if obj.min_order_amount and (amount_total_ship is None or amount_total_ship<obj.min_order_amount):
                msg="Order total is insufficient to use this voucher."
                if obj.min_order_amount_msg:
                    msg=obj.min_order_amount_msg
                raise NFException(msg)
            if obj.new_customer:
                res=get_model("sale.order").search([["contact_id","=",contact_id],["state","!=","voided"]])
                if res:
                    msg="This voucher can only be used by new customers."
                    if obj.new_customer_msg:
                        msg=obj.new_customer_msg
                    raise NFException(msg)
            if obj.exist_customer:
                res=get_model("sale.order").search([["contact_id","=",contact_id],["state","!=","voided"]])
                if not res:
                    msg="This voucher can only be used by existing customers."
                    if obj.exist_customer_msg:
                        msg=obj.exist_customer_msg
                    raise NFException(msg)
            if obj.max_orders_per_customer:
                res=get_model("sale.order").search([["contact_id","=",contact_id],["voucher_id","=",obj.id],["state","!=","voided"]])
                if len(res)>=obj.max_orders_per_customer:
                    msg="The maximum usage limit has been reached for this voucher"
                    if obj.max_orders_per_customer_msg:
                        msg=obj.max_orders_per_customer_msg
                    raise NFException(msg)
            if obj.max_orders: # XXX
                res=get_model("sale.order").search([["voucher_id","=",obj.id],["state","!=","voided"]])
                if len(res)>=obj.max_orders:
                    msg="The maximum usage limit has been reached for this voucher"
                    if obj.max_orders_msg:
                        msg=obj.max_orders_msg
                    raise NFException(msg)
            if obj.sale_id and not obj.sale_id.is_paid: # XXX: what if cancel SO after use voucher?
                raise NFException("Sale order %s is not yet paid"%(obj.sale_id.number))
            if obj.cond_product_categ_id:
                prod_ids=[]
                for line in products:
                    prod_id=line["product_id"]
                    prod_ids.append(prod_id)
                res=get_model("product").search([["id","in",prod_ids],["categ_id","child_of",obj.cond_product_categ_id.id]])
                if not res:
                    msg="Wrong product category"
                    if obj.cond_product_categ_msg:
                        msg=obj.cond_product_categ_msg
                    raise NFException(msg)
            if obj.cond_product_id:
                prod_ids=[]
                for line in products:
                    prod_id=line["product_id"]
                    prod_ids.append(prod_id)
                if obj.cond_product_id.id not in prod_ids:
                    msg="Wrong product"
                    if obj.cond_product_msg:
                        msg=obj.cond_product_msg
                    raise NFException(msg)
            if obj.cond_refer_email:
                found=False
                for order in get_model("sale.order").search_browse([["contact_id.email","=",obj.cond_refer_email]]):
                    if order.is_paid:
                        found=True
                        break
                if not found:
                    msg=obj.cond_refer_message or "Your friend did not order yet"
                    raise NFException(msg)
            qty_check=0
            for line in products:
                if obj.cond_product_id and line.get("product_id")!=obj.cond_product_id.id:
                    continue
                if obj.cond_product_categ_id:
                    prod_id=line.get("product_id")
                    if not prod_id:
                        continue
                    prod=get_model("product").browse(prod_id)
                    if prod.categ_id.id!=obj.cond_product_categ_id:
                        continue
                qty_check+=line.get("qty",1)
            if obj.min_qty and qty_check<obj.min_qty:
                msg="Order qty is too low (%s < %s)"%(qty_check,obj.min_qty)
                if obj.min_qty_msg:
                    msg=obj.min_qty_msg
                raise NFException(msg)
            if obj.qty_multiple and qty_check%obj.qty_multiple!=0:
                msg="Order qty is not a multiple of %s (%s)"%(obj.qty_mutiple,qty_check)
                if obj.qty_multiple_msg:
                    msg=obj.qty_multiple_msg
                raise NFException(msg)
            disc_amt=0
            if obj.benefit_type=="fixed_discount_order":
                disc_amt=min(obj.discount_amount,amount_total_ship or 0)
            elif obj.benefit_type=="percent_discount_order":
                disc_amt=amount_total*(obj.discount_percent or 0)/100
                disc_amt=min(disc_amt,amount_total_ship or 0)
            elif obj.benefit_type=="percent_discount_product":
                disc_amt=0
                for line in products:
                    if line.get("product_id")!=obj.cond_product_id.id:
                        continue
                    disc_amt+=(line.get("amount") or 0)*(obj.discount_percent or 0)/100
                disc_amt=min(disc_amt,amount_total_ship or 0)
            return {
                "discount_amount": disc_amt,
            }
        except NFException as e:
            import traceback
            traceback.print_exc()
            return {
                "discount_amount": 0,
                "error_message": str(e),
            }

Voucher.register()
