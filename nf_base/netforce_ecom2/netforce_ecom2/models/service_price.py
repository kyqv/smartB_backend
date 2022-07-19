from netforce.model import Model,fields,get_model

class ServicePrice(Model):
    _name="service.price"
    _string="Service Pricing"
    _name_field="code"
    _fields={
        "code": fields.Char("Code",required=True),
        "product_id": fields.Many2One("product","Service", required=True),
        "unit_price": fields.Decimal("Price per Unit", required=True),
    }

    _keys=["code","product_id"]

ServicePrice.register()
