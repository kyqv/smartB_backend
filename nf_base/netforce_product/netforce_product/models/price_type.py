from netforce.model import Model,fields,get_model

class PriceType(Model):
    _name="price.type"
    _string="Price Type"
    _fields={
        "name": fields.Char("Name",required=True),
        "currency_id": fields.Many2One("currency","Currency",required=True),
        "uom_id": fields.Many2One("uom","UoM",required=True),
        "price_format": fields.Char("Price format"),
        "price_format_factor": fields.Decimal("Price format factor",scale=6),
    }

    def convert(self,price,from_id,to_id,context={}):
        #print("PriceType.convert",price,from_id,to_id)
        pt_from=self.browse(from_id)
        pt_to=self.browse(to_id)
        price_qty=get_model("uom").convert(price,pt_to.uom_id.id,pt_from.uom_id.id,context=context)
        #print("price_qty",price_qty)
        price_cur=get_model("currency").convert(price_qty,pt_from.currency_id.id,pt_to.currency_id.id,context=context)
        #print("price_cur",price_cur)
        return price_cur

PriceType.register()
