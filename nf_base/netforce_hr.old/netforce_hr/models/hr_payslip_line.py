from netforce.model import Model, fields, get_model
from datetime import *
from dateutil.relativedelta import *

class PaySlipLine(Model):
    _name="hr.payslip.line"
    _string="Pay Slip Line"
    
    def _get_all(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            item=obj.payitem_id
            type=item.type
            res[obj.id]={
                'pay_type': get_model('hr.payitem').get_paytype(context={'type': type}),
            }
        return res

    _fields={
        "slip_id": fields.Many2One("hr.payslip","Pay Slip",required=True,on_delete="cascade"),
        "payitem_id": fields.Many2One("hr.payitem","Pay Item",required=True),
        "qty": fields.Decimal("Qty",required=True),
        "rate": fields.Decimal("Rate",required=True),
        "amount": fields.Decimal("Amount",function="get_amount"),
        "comments": fields.One2Many("message","related_id","Comments"),
        'pay_type': fields.Selection([['income','Income'],['deduct','Deduct'],['contrib','Contrib'],['other','Other']],'Type',function="_get_all",function_multi=True,store=True),
    }
    _defaults={
        "state": "draft",
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
    }
    _order="pay_type desc"

    def get_amount(self,ids,context={}):
        #  TODO need some logic for compute pay item
        vals={}
        for obj in self.browse(ids):
            slip=obj.slip_id
            vals[obj.id]=obj.qty*obj.rate*(slip.currency_rate or 1)
        return vals
    
    def create(self,vals,**kw):
        new_id=super().create(vals,**kw)
        self.function_store([new_id])
        return new_id

    def write(self,ids,vals,**kw):
        self.function_store(ids)
        super().write(ids,vals,**kw)

PaySlipLine.register()
