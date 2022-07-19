from netforce.model import Model, fields, get_model


class Pallet(Model):
    _name = "stock.pallet"
    _string = "Pallet"
    _fields = {
        "name": fields.Char("Name", required=True),
        "code": fields.Char("Code"),
        "description": fields.Text("Description"),
        "width": fields.Decimal("Width"),
        "height": fields.Decimal("Height"),
        "length": fields.Decimal("Length"),
        "weight": fields.Decimal("Weight"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
    }
    _order = "name"

Pallet.register()
