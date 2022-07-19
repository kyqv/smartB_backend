from netforce.model import Model, fields
from netforce.access import get_active_company

class Department(Model):
    _name="hr.department"
    _string="Department"
    _key=["name"]
    _multi_company=True

    _fields={
        "name": fields.Char("Name",required=True,search=True),
        "code": fields.Char("Code"),
        "comments": fields.One2Many("message","related_id","Comments"),
        'company_id': fields.Many2One("company",'Company'),
    }
    _order="name"
    _defaults={
        'company_id': lambda *a: get_active_company(),
    }

Department.register()
