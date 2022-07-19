from netforce.model import Model,fields,get_model

class PackagePrice(Model):
    _name="package.price"
    _string="Package Pricing"
    _name_field="code"
    _fields={
        "code": fields.Char("Code", required=True),
        "description": fields.Text("Description", translate=True),
        "unit_price": fields.Decimal("Price per Unit", required=True),
    }

    _keys=["code"]

PackagePrice.register()
