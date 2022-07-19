from netforce.model import Model, fields, get_model

class PayslipTemplateLine(Model):
    _name="hr.payslip.template.line"
    _string="Payslip Template Line"

    def _get_amount(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            vals={
                'currency_rate': 1,
            }
            if obj.currency_id:
                vals['currency_rate']=obj.currency_id.sell_rate or 1
            vals['amount']=(obj.qty or 0)*(obj.rate or 0) * vals['currency_rate'] # XXX
            res[obj.id]=vals
        return res

    _fields={
        'template_id': fields.Many2One("hr.payslip.template","Payslip Template",required=True,on_delete="cascade"),
        'payitem_id': fields.Many2One("hr.payitem","Pay Item",required=True),
        'currency_id': fields.Many2One("currency","Currency"),
        'currency_rate': fields.Decimal("Currency Rate",function="_get_amount",function_multi=True),
        'regular': fields.Boolean("Regular"),
        'qty': fields.Decimal("Qty"),
        'rate': fields.Decimal("Rate"),
        'amount': fields.Decimal("Amount", function="_get_amount",function_multi=True),
    }

    def get_salary(self,context={}):
        template_id=context.get('template_id')
        if not template_id:
            return 0
        dom=[['template_id','=',template_id]]
        salary=0
        for obj in self.search_browse(dom):
            item=obj.payitem_id
            if item.type=='wage':
                if item.wage_type=='salary':
                    salary+=obj.amount or 0
        return salary
    
    def _get_default_currency(self,context={}):
        currency_ids=get_model('currency').search([])
        if currency_ids:
            return currency_ids[0]

    _defaults={
        'currency_id': _get_default_currency,
        'regular': True,
    }

PayslipTemplateLine.register()
