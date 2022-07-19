from netforce.model import Model, fields, get_model
import time
from netforce import access

from pprint import pprint
class Attendance(Model):
    _name="hr.attendance"
    _string="Attendance Event"
    _audit_log=True

    _fields={
        "employee_id": fields.Many2One("hr.employee","Employee",required=True,search=True),
        "time": fields.DateTime("Time",required=True,search=True),
        "action": fields.Selection([["sign_in","Sign In"],["sign_out","Sign Out"]],"Action",required=True,search=True),
        "mode": fields.Selection([["manual","Manual"],["auto","Auto"],["csv","CSV"]],"Mode",readonly=True),
        "comments": fields.One2Many("message","related_id","Comments"),
    }
    _order="time desc"

    def _employee(self,context={}):
        uid =  access.get_active_user()
        users = get_model("hr.employee").search([
                ['user_id','=',uid]
            ],limit=1)
        return users and users[0] or False

    _defaults={
        "time": lambda *a: time.strftime("%Y-%m-%d %H:%M:S"),
        "employee_id": _employee,
        "action": lambda self,context : context.get('action','sign_in'),
        "mode": "manual",
    }

Attendance.register()
