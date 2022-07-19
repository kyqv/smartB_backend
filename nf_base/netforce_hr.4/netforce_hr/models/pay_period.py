from datetime import datetime, timedelta

from netforce.model import Model, fields

class PayPeriod(Model):
    _name="hr.pay.period"
    _string="Pay Period"
    
    _fields={
        "name": fields.Char("Name", required=True, search=True),
        "year": fields.DateTime("Year"),
        'lines': fields.One2Many("hr.pay.period.line","period_id", "Lines"),
    }

PayPeriod.register()
