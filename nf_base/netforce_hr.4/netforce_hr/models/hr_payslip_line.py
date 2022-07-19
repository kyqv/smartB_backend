from netforce.model import Model, fields, get_model
from datetime import *
from dateutil.relativedelta import *

class PaySlipLine(Model):
    _name="hr.payslip.line"
    _string="Pay Slip Line"
    
    _fields={
        "slip_id": fields.Many2One("hr.payslip","Pay Slip",required=True,on_delete="cascade"),
        "payitem_id": fields.Many2One("hr.payitem","Pay Item",required=True),
        "qty": fields.Decimal("Qty"),
        "rate": fields.Decimal("Rate"),
        "amount": fields.Decimal("Amount",required=True),
        "sequence": fields.Integer("Sequence"),
    }
    _defaults={
        "state": "draft",
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
    }

PaySlipLine.register()
