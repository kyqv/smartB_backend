from datetime import datetime, timedelta

from netforce.model import Model, fields

class PayPeriodLine(Model):
    _name="hr.pay.period.line"
    _string="Pay Period Line"
    
    _fields={
        'period_id': fields.Many2One("hr.pay.period","Pay Period",required=True),
        'time_start': fields.DateTime("Time Start",required=True),
        'time_stop': fields.DateTime("Time Start",required=True),
    }

PayPeriodLine.register()
