from netforce.model import Model, fields, get_model


class SellerCom(Model):
    _name = "seller.commission"
    _string = "Seller Commission"
    _fields = {
        "seller_id": fields.Many2One("seller","Seller",required=True,search=True),
        "sequence": fields.Integer("Sequence"),
        "customer_id": fields.Many2One("contact","Customer"),
        "customer_group_id": fields.Many2One("contact.group","Customer Group"),
        "commission_percent": fields.Decimal("Commission (%)"),
        "min_amount": fields.Decimal("Threshold Amount"),
    }
    _order="sequence,id"

SellerCom.register()
