from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path, get_file_path
from netforce.access import get_active_company
from netforce.database import get_connection
from . import utils
import re
from datetime import *
from dateutil.relativedelta import *
from calendar import monthrange

class PaySlip(Model):
    _name="hr.payslip"
    _string="Pay Slip"
    _multi_company=True
    _name_field="employee_id"

    _fields={
        "run_id": fields.Many2One("hr.payrun","Pay Run",search=True,required=True,on_delete="cascade"),
        "employee_id": fields.Many2One("hr.employee","Employee",required=True,search=True ,condition=[["work_status","=","working"]]),
        "date_from": fields.Date("From"),
        "date_to": fields.Date("To"),
        "due_date": fields.Date("Due Date"),
        "lines": fields.One2Many("hr.payslip.line","slip_id","Lines"),
        "comments": fields.One2Many("message","related_id","Comments"),
        "state": fields.Selection([["draft","Draft"],["approved","Approved"],['paid','Paid'],['posted','Posted']],"Status",required=True),
        "company_id": fields.Many2One("company","Company"),
        "move_id": fields.Many2One("account.move","Journal Entry"),
        "department_id": fields.Many2One("hr.department","Department"),
        "currency_id": fields.Many2One("currency","Currency"),
        "amount_salary" : fields.Decimal("Salary",function="get_totals",function_multi=True),
        "amount_overtime" : fields.Decimal("Overtime",function="get_totals",function_multi=True),
        "amount_mobile" : fields.Decimal("Mobile",function="get_totals",function_multi=True),
        "amount_travel" : fields.Decimal("Travel",function="get_totals",function_multi=True),
        "amount_commission" : fields.Decimal("Commission",function="get_totals",function_multi=True),
        "amount_other_income" : fields.Decimal("Other Income",function="get_totals",function_multi=True),
        "amount_total_income" : fields.Decimal("Total Income",function="get_totals",function_multi=True),
        "amount_tax" : fields.Decimal("Tax",function="get_totals",function_multi=True),
        "amount_sso" : fields.Decimal("SSO",function="get_totals",function_multi=True),
        "amount_pvd" : fields.Decimal("PVD",function="get_totals",function_multi=True),
        "amount_other_expense" : fields.Decimal("Other Expenses",function="get_totals",function_multi=True),
        "amount_total_expense" : fields.Decimal("Total Expenses",function="get_totals",function_multi=True),
        "amount_net" : fields.Decimal("Net Pay",function="get_totals",function_multi=True),
    }

    def _get_currency(self,context={}):
        st=get_model('settings').browse(1)
        currency_id=st.currency_id.id
        return currency_id

    _defaults={
        "state": "draft",
        "date_from": lambda *a: date.today().strftime("%Y-%m-%d"),
        "date_to": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
        "due_date": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
        "company_id": lambda *a: get_active_company(),
        'currency_id': _get_currency,
    }
    _order="run_id.date_from desc,employee_id.code,employee_id.first_name"

    def get_totals(self,ids,context={}):
        all_vals={}
        for obj in self.browse(ids):
            totals={}
            for line in obj.lines:
                item=line.payitem_id
                if not item:
                    continue
                totals.setdefault(item.type,0)
                totals[item.type]+=line.amount
            inc_types=["salary","overtime","mobile","travel","commission","other_income"]
            exp_types=["tax","sso","pvd","other_expense"]
            vals={}
            tot_inc=0
            for t in inc_types:
                amt=totals.get(t,0)
                vals["amount_"+t]=amt
                tot_inc+=amt
            vals["amount_total_income"]=tot_inc
            tot_exp=0
            for t in exp_types:
                amt=-totals.get(t,0)
                vals["amount_"+t]=amt
                tot_exp+=amt
            vals["amount_total_expense"]=tot_exp
            vals["amount_net"]=tot_inc-tot_exp
            all_vals[obj.id]=vals
        return all_vals

    def update_amounts(self,context={}):
        data=context["data"]
        path=context["path"]
        line=get_data_path(data,path,parent=True)
        line["amount"]=line["qty"]*line["rate"]
        return data

PaySlip.register()
