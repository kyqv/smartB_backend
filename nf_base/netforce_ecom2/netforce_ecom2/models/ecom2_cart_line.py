from netforce.model import Model,fields,get_model
import time
import math

class CartLine(Model):
    _name="ecom2.cart.line"
    _string="Cart Line"
    _audit_log=True
    _fields={
        "sequence": fields.Integer("Sequence"),
        "cart_id": fields.Many2One("ecom2.cart","Cart",required=True,on_delete="cascade"),
        "product_id": fields.Many2One("product","Product",required=True),
        "lot_id": fields.Many2One("stock.lot","Lot / Serial Number"),
        "weight": fields.Decimal("Weight",function="_get_related",function_context={"path": "lot_id.weight"}),
        "unit_price": fields.Decimal("Unit Price",required=True),
        "qty": fields.Decimal("Qty",required=True),
        "qty_int": fields.Integer("Qty",function="get_qty_int"),
        "uom_id": fields.Many2One("uom","UoM",required=True),
        "amount": fields.Decimal("Amount",function="get_amount"),
        "delivery_date": fields.Date("Delivery Date"),
        "ship_address_id": fields.Many2One("address","Shipping Address"),
        "delivery_slot_id": fields.Many2One("delivery.slot","Delivery Slot"),
        "qty_avail": fields.Decimal("Qty In Stock",function="get_qty_avail"),
        "delivery_delay": fields.Integer("Delivery Delay (Days)",function="get_delivery_delay"),
        "delivery_weekdays": fields.Char("Delivery Weekdays",function="_get_related",function_context={"path":"product_id.delivery_weekdays"}),
        "packaging_id": fields.Many2One("stock.packaging","Packaging"),
        "ship_method_id": fields.Many2One("ship.method","Shipping Method"),
        "addons": fields.Many2Many("product.addon","Addons"),
        "discount": fields.Decimal("Discount"),
    }

    def get_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=obj.unit_price*obj.qty-(obj.discount or 0)
        return vals

    def create(self,vals,*args,**kw):
        prod_id=vals["product_id"]
        prod=get_model("product").browse(prod_id)
        vals["uom_id"]=prod.uom_id.id
        if not vals.get("unit_price"):
            if prod.sale_invoice_uom_id.name=="KG": # XXX: too specific
                lot_id=vals.get("lot_id")
                if lot_id:
                    lot=get_model("stock.lot").browse(lot_id)
                    sale_price=math.ceil((prod.sale_price or 0)*(lot.weight or 0)/1000) # XXX: too specific
                else:
                    sale_price=math.ceil((prod.sale_price or 0)*(prod.sale_to_invoice_uom_factor or 0)) # XXX: too specific
                vals["unit_price"]=sale_price or 0
            else:
                vals["unit_price"]=prod.sale_price or 0
        return super().create(vals,*args,**kw)

    def get_qty_avail(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            prod=obj.product_id
            loc_ids=[loc.location_id.id for loc in prod.locations]
            cond=[["product_id","=",prod.id],["location_id","in",loc_ids]]
            if obj.lot_id:
                cond.append(["lot_id","=",obj.lot_id.id])
            qty=0
            for bal in get_model("stock.balance").search_browse(cond):
                qty+=bal.qty_virt
            vals[obj.id]=qty
        return vals

    def get_delivery_delay(self,ids,context={}):
        settings=get_model("ecom2.settings").browse(1)
        vals={}
        for obj in self.browse(ids):
            delay=0
            prod=obj.product_id
            if obj.qty_avail<=0 and not prod.sale_lead_time_nostock == 0: ### REVIEW 
                delay=max(delay,prod.sale_lead_time_nostock or settings.sale_lead_time_nostock or 0)
            vals[obj.id]=delay
        return vals

    def set_qty(self,ids,qty,context={}):
        print("CartLine.set_qty",ids,qty)
        obj=self.browse(ids[0])
        if obj.cart_id.state!="draft":
            raise Exception("Invalid cart status")
        line_id=ids[0]
        if qty==0:
            get_model("ecom2.cart.line").delete([line_id])
        else:
            get_model("ecom2.cart.line").write([line_id],{"qty":qty})

    def get_qty_int(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=int(obj.qty)
        return vals

CartLine.register()
