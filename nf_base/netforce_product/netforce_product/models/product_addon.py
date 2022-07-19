from netforce.model import Model, fields


class Addon(Model):
    _name = "product.addon"
    _string = "Product Addon"
    _key=["code"]
    _fields = {
        "name": fields.Char("Addon Name", required=True, search=True),
        "code": fields.Char("Addon Code", required=True, search=True),
        "sale_price": fields.Decimal("Sales Price"),
    }
    _order="name"

Addon.register()
