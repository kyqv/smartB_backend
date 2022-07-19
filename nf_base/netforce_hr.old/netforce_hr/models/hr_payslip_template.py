from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path
from netforce.access import get_active_company
from datetime import *

class PayslipTemplate(Model):
    _name="hr.payslip.template"
    _string="Payslip Template"
    _multi_company = True
    
    def _get_name(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            emp_code=obj.employee_id.code or ''
            res[obj.id]=emp_code #XXX
        return res

    _fields={
        "name": fields.Char("Name",function="_get_name",store=True,search=True),
        'employee_id': fields.Many2One("hr.employee","Employee",required=True,search=True,condition=[["work_status","=","working"],["payslip_template_id","=",None]]),
        'payitem_profile_id': fields.Many2One('hr.payitem.profile','Pay Item Profile',required=True,search=True),
        'lines': fields.One2Many('hr.payslip.template.line','template_id','Lines'),
        "description": fields.Text("Description"),
        "comments": fields.One2Many("message","related_id","Comments"),
        "company_id": fields.Many2One("company","Company"),
    }
    _defaults={
        "company_id": lambda *a: get_active_company(),
    }

    _order="name"

    def get_income(self,ids,context={}):
        obj=self.browse(ids)[0]
        income=0
        for line in obj.lines:
            item=line.payitem_id
            if not item.include_tax:
                continue 
            if item.type in ('wage', 'allow'):
                income+=line.amount or 0
        return income

    def create(self,vals,**kw):
        new_id=super().create(vals,**kw)
        self.function_store([new_id])
        emp_id = vals['employee_id']
        if emp_id:
            temp = self.search_browse([['employee_id','=',emp_id]])[0]
            if temp:
                emp = temp.employee_id
                if emp and not emp.payslip_template_id:
                    emp.write({
                        'payslip_template_id': new_id,
                    })
        return new_id

    def write(self,ids,vals,**kw):
        super().write(ids,vals,**kw)
        self.function_store(ids)

    def onchange_profile(self,context={}):
        currencys=get_model('currency').search_browse([])
        currency_id=None
        currency_rate=1
        if currencys:
            currency=currencys[0]
            currency_id=currency.id
            currency_rate=currency.sell_rate or 1
        data=context['data']
        profile_id=data['payitem_profile_id']
        profile=get_model('hr.payitem.profile').browse(profile_id)
        data['lines']=[]
        for item in profile.pay_items:
            data['lines'].append({
                'payitem_id': item.id,
                'currency_id': currency_id,
                'currency_rate': currency_rate,
            })
        return data

    def onchange_line(self,context={}):
        data=context['data']
        path=context['path']
        line=get_data_path(data,path,parent=True)
        currency_id=line['currency_id']
        if currency_id:
            currency=get_model('currency').browse(currency_id)
            line['currency_rate']=currency.sell_rate or 1
        line['amount']=(line['qty'] or 0) * (line['rate'] or 0) * line['currency_rate']
        #data=self.update_tax(data)
        #data=self.update_sso(data)
        return data
    
    def update_tax(self,data):
        tax_item=None
        tax_index=-1
        count=0
        year_income=0
        for line in data['lines']:
            amt=line['amount'] or 0
            item_id=line['payitem_id']
            item=get_model('hr.payitem').browse(item_id)
            if item.type=='tax' and item.tax_type=='thai':
                tax_index=count
                tax_item=item
            if not item.include_tax:
                continue
            if item.type in ('wage', 'allow'):
                year_income+=amt
                if item.wage_type=='salary':
                    salary=amt
            elif item.type=='deduction':
                year_income-=amt
            count+=1
        if tax_index>-1 and tax_item:
            ctx={
                'employee_id': data['employee_id'],
                'year_income': year_income*12,
                'salary': salary,
            }
            qty,rate=tax_item.compute(context=ctx) # regular income tax
            line=data['lines'][tax_index]
            line['qty']=qty
            line['rate']=rate
            line['amount']=qty*rate
        return data

    def update_sso(self,data):
        sso_item=None
        sso_index=-1
        count=0
        year_income=0
        for line in data['lines']:
            amt=line['amount'] or 0
            item_id=line['payitem_id']
            item=get_model('hr.payitem').browse(item_id)
            if item.type=='deduct' and item.deduct_type=='thai_social':
                sso_index=count
                sso_item=item
            if not item.include_sso:
                continue
            if item.type in ('wage', 'allow'):
                year_income+=amt
                if item.wage_type=='salary':
                    salary=amt
            elif item.type=='deduction':
                year_income-=amt
            count+=1
        if sso_index>-1 and sso_item:
            ctx={
                'employee_id': data['employee_id'],
                'year_income': year_income*12,
                'salary': salary,
            }
            qty,rate=sso_item.compute(context=ctx) # regular income sso
            line=data['lines'][sso_index]
            line['qty']=qty
            line['rate']=rate
            line['amount']=qty*rate
        return data

    def onchange_item_line(self,context={}):
        data=context['data']
        path=context['path']
        employee_id=data['employee_id']
        ctx={
            'employee_id': employee_id,
        }
        line=get_data_path(data,path,parent=True)
        currency_id=line['currency_id']
        if currency_id:
            currency=get_model('currency').browse(currency_id)
            line['currency_rate']=currency.sell_rate or 1
        item_id=line['payitem_id']
        if item_id:
            item=get_model('hr.payitem').browse(item_id)
            qty,rate=0,0
            if item.type=='tax':
                data=self.update_tax(data)
            else:
                qty,rate=item.compute(context=ctx)
                line['qty']=qty
                line['rate']=rate
                line['amount']=line['qty'] * line['rate'] * line['currency_rate']
        return data
    
    def onchange_employee(self,context={}):
        data=context['data']
        date_time = date.today().strftime("%Y-%m-%d")
        employee_id=data['employee_id']
        ctx={
            'employee_id': employee_id,
            'year_date': date_time,
        }
        emp = get_model("hr.employee").browse(employee_id)
        for line in data['lines']:
            item_id=line['payitem_id']
            if item_id:
                item=get_model('hr.payitem').browse(item_id)
                qty,rate=item.compute(context=ctx)
                line['qty']=qty
                if item.type == "tax" and item.tax_type == "thai":
                    line['rate'] = 0
                elif item.type == "wage" and item.wage_type == "salary":
                    line['rate'] = emp.salary
                else:
                    line['rate']=rate
        return data

PayslipTemplate.register()


