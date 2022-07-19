from netforce.model import Model,fields,get_model

class ProductFulfillment(Model):
    _name="product.fulfillment"
    _string="Product Fulfillment"
    _fields={
        "fulfillment_product_id": fields.Many2One("product","Fulfillment Id", on_delete="cascade"),
        "product_id": fields.Many2One("product","Product",required=True),
        "uom_id": fields.Many2One("uom","UoM",required=True),
        "unit_price": fields.Decimal("Unit Price",required=True, scale=6),
        "qty": fields.Integer("Qty",required=True),
        "type": fields.Selection([("in","In"),("out","Out")],"Type",required=True),
        #"currency_id": fields.Many2One("currency","Currency",required=True),
    }
    
    """
    def convert(self,price,from_id,to_id,context={}):
        #print("PriceType.convert",price,from_id,to_id)
        pt_from=self.browse(from_id)
        pt_to=self.browse(to_id)
        price_qty=get_model("uom").convert(price,pt_to.uom_id.id,pt_from.uom_id.id,context=context)
        #print("price_qty",price_qty)
        price_cur=get_model("currency").convert(price_qty,pt_from.currency_id.id,pt_to.currency_id.id,context=context)
        #print("price_cur",price_cur)
        return price_cur
    """

ProductFulfillment.register()
