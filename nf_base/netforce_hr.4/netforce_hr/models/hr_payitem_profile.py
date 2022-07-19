from netforce.model import Model, fields
from netforce.access import get_active_company

class PayItemProfile(Model):
    _name="hr.payitem.profile"
    _string="Pay Item Profile"
    _multi_company = True

    _fields={
        "name": fields.Char("Name",required=True,search=True),
        'pay_items': fields.Many2Many("hr.payitem", "Pay Items"),
        "company_id": fields.Many2One("company","Company"),
    }
    _defaults={
        "company_id": lambda *a: get_active_company(),
    }

PayItemProfile.register()
