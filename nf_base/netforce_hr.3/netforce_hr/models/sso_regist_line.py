import time
from netforce.model import Model, fields, get_model
from . import utils
from netforce.access import get_active_company

class SsoRegistLine(Model):
    _name="sso.regist.line"
    _string="Sso Regist Line"
    _fields={
        "sso_regist_id": fields.Many2One("sso.regist","Sso Regist",required=True,on_delete="cascade"),
        "employee_id": fields.Many2One("hr.employee","Employee"),
        "id_no": fields.Char("ID No."),
        "hire_date": fields.Date("Hire Date"),
        "old_company": fields.Char("Old Company"),
        "other_old_company": fields.Char("Other Old Company"),
    }


SsoRegistLine.register()
