from netforce.model import Model, fields, get_model
from netforce import database

class Contract(Model):
    _name="hr.contract"
    _string="Contract"

    _fields={
        "name": fields.Char("Contract Reference",search=True),
        "employee_id": fields.Many2One("hr.employee","Employee",search=True),
    }

    _defaults={
    }
    _order=""

Contract.register()
