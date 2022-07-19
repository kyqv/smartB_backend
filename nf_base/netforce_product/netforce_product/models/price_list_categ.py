from netforce.model import Model, fields


class PriceListCateg(Model):
    _name = "price.list.categ"
    _string = "Price List Category"
    _fields = {
        "list_id": fields.Many2One("price.list", "Price List", required=True, on_delete="cascade", search=True),
        "categ_id": fields.Many2One("product.categ","Product Category", required=True),
        "discount_percent": fields.Decimal("Discount %"),
        "discount_text": fields.Char("Discount Text"),
    }

PriceListCateg.register()
