from netforce.model import Model, fields, get_model


class ContainerType(Model):
    _name = "stock.container.type"
    _string = "Container Type"
    _fields = {
        "name": fields.Char("Name", required=True),
        "code": fields.Char("Code"),
        "description": fields.Text("Description"),
        "width": fields.Decimal("Width"),
        "height": fields.Decimal("Height"),
        "length": fields.Decimal("Length"),
        "weight": fields.Decimal("Weight"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "num_items": fields.Integer("Number Of Items"),
    }
    _order = "name"

ContainerType.register()
