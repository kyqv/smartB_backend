import time
from netforce.model import Model, fields, get_model
from . import utils
from netforce.access import get_active_company

class SsoQuitsLine(Model):
    _name="sso.quits.line"
    _string="Sso Quits Line"
    _fields={
        "sso_quits_id": fields.Many2One("sso.quits","Sso Quits",required=True,on_delete="cascade"),
        "employee_id": fields.Many2One("hr.employee","Employee"),
        "id_no": fields.Char("ID No."),
        "resign_date": fields.Date("Resign Date"),
        "reason": fields.Selection([["1","1 Resign"],["2","2 End of the employment term"],["3","3 Lay off"],["4","4 Retire"],["5","5 Fired"],["6","6 Died"],["7","7 Branch transfer"]],"Reason of quits"),
    }


SsoQuitsLine.register()
