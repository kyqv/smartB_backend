from netforce.model import Model, fields, get_model
from decimal import *

class PayItem(Model):
    _name="hr.payitem"
    _string="Pay Item"

    def get_paytype(self,context={}):
        pay_type='other'
        if not context:
            return pay_type
        type=context.get('type')
        if type in ('wage', 'allow'):
            pay_type='income'
        elif type in ('deduct','tax'):
            pay_type='deduct'
        elif type in ('contrib'):
            pay_type='contrib'
        return pay_type

    _fields={
        "name": fields.Char("Name",required=True,search=True),
        "description": fields.Text("Description"),
        "type": fields.Selection([
            ["wage","Wages"],
            ["allow","Allowances"],
            ["deduct","Deductions"],
            ["tax","Tax"],
            #["post_allow","Non-taxable Allowances"],
            #["post_deduct","Post-tax Deductions"],
            ["contrib","Employer Contributions"]
            ],"Pay Item Type",required=True,search=True),
        "account_id": fields.Many2One("account.account","Account",multi_company=True),
        "acc_type": fields.Selection([["debit","Debit"],['credit','Credit']],"Account Type"),
        "show_default": fields.Boolean("Show as default for all employees"),
        "comments": fields.One2Many("message","related_id","Comments"),
        "active": fields.Boolean("Active"),
        "include_tax": fields.Boolean("Include Tax"),
        "include_sso": fields.Boolean("Include SSO"),
        "include_pnd1": fields.Boolean("Include PND1"),
        "fix_income": fields.Boolean("Fix Income"),
        "tax_type": fields.Selection([["thai","Thai Personal Income Tax"]],"Tax Type"),
        "deduct_type": fields.Selection([["thai_social","Thai Social Security Fund"],["provident","Provident Fund"],['loan','Loan']],"Deduction Type"),
        "contrib_type": fields.Selection([["sso","Thai Social Security Fund Accum"],['prov','Provident Fund Accum']],"Contrib Type"),
        "wage_type": fields.Selection([["salary","Salary"],["overtime","Overtime"],["bonus","Bonus"],["commission","Commission"],['position',"Position Allowance"]],"Wage Type"),
        "times": fields.Decimal("Times"),
        "months": fields.Integer("Number of Month"),
    }

    _defaults={
        "active": True,
        'include_tax': True,
        'include_sso': True,
        'include_pnd1':True,
    }
    _order="name"

    def compute(self,ids,context={}):
        qty=1
        rate=0
        obj=self.browse(ids)[0]

        date_to = context.get("date_to") or context.get("year_date")
        if date_to:
            to_year,to_month,to_day=date_to.split("-")
            to_month=int(to_month)
            to_year=int(to_year)

        emp_id=context.get("employee_id")
        if not emp_id:
            return qty,rate
        emp=get_model("hr.employee").browse(emp_id)
        hire_date=emp.hire_date
        hire_year,hire_month,hire_day=hire_date.split("-")
        hire_month=int(hire_month)
        hire_year=int(hire_year)
        hire_day=int(hire_day)

        if obj.type=="wage":
            if obj.wage_type=="salary" and emp.salary:
                qty=1
                salary_month=emp.salary or 0
                if hire_year == to_year and hire_month == to_month:
                    salary_day = salary_month / Decimal(30)
                    if hire_day == 1:
                        day = 30
                    if hire_month == 2:
                        day = 29 - hire_day
                    elif hire_month in (4,6,9,11):
                        day = 31 - hire_day
                    else:
                        day = 32 - hire_day
                    salary = salary_day * day
                else:
                    salary = salary_month
                # XXX get total day woking for each month
                if emp.work_type=='daily':
                    date_from=context.get("date_from")
                    date_to=context.get("date_to")
                    if date_from and date_to:
                        res='%s-%s'%(int(date_to[8:10]),int(date_from[8:10]))
                        total_day=eval(res)
                        #cond=[['time','>=',date_from],['time','<=',date_to],['employee_id','=',emp.id]]
                        #att=get_model("hr.attendance").search_read(cond)
                        #if att: print(att)
                        print('total_day ', total_day)
                        qty=30 # XXX
                rate=salary
            elif obj.wage_type=='overtime' and emp.salary:
                qty=0 #XXX
                if emp.work_type=='daily':
                    rate=emp.salary/Decimal(8)*(obj.times or 0)
                else:
                    rate=emp.salary/Decimal(30)/Decimal(8)*(obj.times or 0)
            elif obj.wage_type=='bonus' and emp.salary:
                qty=1
                rate=emp.salary*(obj.months or 0)
        elif obj.type=="deduct":
            if obj.deduct_type=="thai_social":
                qty=1
                context['salary_first'] = False
                if hire_year == to_year and hire_month == to_month:
                    context['salary_first'] = True
                rate=self.compute_thai_social(context=context)
            if obj.deduct_type=="provident":
                qty=1
                rate=self.compute_provident(context=context)
        elif obj.type=="tax":
            if obj.tax_type=="thai":
                qty=1
                rate=self.compute_thai_tax(context=context)["tax_month"]
        elif obj.type=='contrib':
            if obj.contrib_type=='prov':
                qty=1
                rate=self.compute_provident_acc(context=context)
            elif obj.contrib_type=='sso':
                qty=1
                context['salary_first'] = False
                if hire_year == to_year and hire_month == to_month:
                    context['salary_first'] = True
                rate=self.compute_thai_social_accu(context=context)
        return qty,rate

    def compute_thai_social(self,context={}):
        emp_id=context.get("employee_id")
        first_salary = context.get("salary_first")
        last_salary = context.get("salary_last")
        if emp_id!='null':
            emp_id=int(emp_id)
        emp=get_model("hr.employee").browse(emp_id)
        if not emp.social_register:
            return 0
        if emp.age >= 60:
            return 0
        hire_date=emp.hire_date
        hire_year,hire_month,hire_day=hire_date.split("-")
        hire_month=int(hire_month)
        hire_year=int(hire_year)
        hire_day=int(hire_day)
        resign_date = emp.resign_date
        if resign_date:
            resign_year,resign_month,resign_day=resign_date.split("-")
            resign_day = int(resign_day)
            resign_year = int(resign_year)
            resign_month = int(resign_month)
        settings=get_model("hr.payroll.settings").browse(1)
        salary = 0
        payslip_template = emp.payslip_template_id
        if payslip_template:
            for line in payslip_template.lines:
                if line.payitem_id.type in ("wage","allow"):
                    if first_salary:
                        rate_day = (line.rate or 0) / Decimal(30)
                        if hire_day == 1:
                            day = 30
                        elif hire_month == 2:
                            day = 29 - hire_day
                        elif hire_month in (4,6,9,11):
                            day = 31 - hire_day
                        else:
                            day = 32 - hire_day
                        salary += rate_day * day
                    elif last_salary:
                        rate_day = line.rate / Decimal(30)
                        if resign_month == 2 and resign_day == 28 or resign_day == 29:
                            day = 30
                        elif resign_day > 30:
                            day = 30
                        else:
                            day = resign_day
                        salary += rate_day * day
                    else:
                        salary += line.rate or 0
        else:
            salary=emp.salary or 0
        if settings.social_min_wage is not None and salary<settings.social_min_wage:
            return 0
        if settings.social_max_wage is not None and salary>settings.social_max_wage:
            salary=settings.social_max_wage
        amt_all=salary*(settings.social_rate or 0)/Decimal(100)
        amt = round(amt_all)
        return amt

    def compute_thai_social_accu(self,context={}):
        amt=self.compute_thai_social(context=context)
        return amt*2

    def compute_provident(self,context={}):
        emp_id=context.get("employee_id")
        emp=get_model("hr.employee").browse(emp_id)
        last_salary = context.get("salary_last")
        first_salary = context.get("salary_first")
        salary=emp.salary or 0
        if not emp.prov_regis:
            return 0
        hire_date=emp.hire_date
        hire_year,hire_month,hire_day=hire_date.split("-")
        hire_month=int(hire_month)
        hire_year=int(hire_year)
        hire_day=int(hire_day)
        resign_date = emp.resign_date
        if resign_date:
            resign_year,resign_month,resign_day=resign_date.split("-")
            resign_day = int(resign_day)
            resign_year = int(resign_year)
            resign_month = int(resign_month)
        if first_salary:
            rate_day = salary / Decimal(30)
            if hire_day == 1:
                day = 30
            elif hire_month == 2:
                day = 29 - hire_day
            elif hire_month in (4,6,9,11):
                day = 31 - hire_day
            else:
                day = 32 - hire_day
            salary = rate_day * day
        if last_salary:
            rate_day = salary / Decimal(30)
            if resign_month == 2 and resign_day == 28 or resign_day == 29:
                day = 30
            elif resign_day > 30:
                day = 30
            else:
                day = resign_day
            salary = rate_day * day
        amt=salary*(emp.prov_rate_employee or 0)/Decimal(100)
        return amt

    def compute_provident_acc(self,context={}):
        amt=self.compute_provident(context=context)
        return amt*2

    def compute_thai_tax(self,context={}):
        # print('compute_thai_tax ', context)
        emp_id=context.get("employee_id")
        if emp_id!='null':
            emp_id=int(emp_id)
        emp=get_model("hr.employee").browse(emp_id)
        period=context.get("period") or 12
        tax_prof=emp.tax_profile_id
        if not tax_prof and emp.tax_register:
            raise Exception("Employee code %s has not tax profile "%(emp.code))
        tax_payer=30000
        pc_gross_income=Decimal(0.4)
        not_exceed=60000
        taxyear_id=None
        # reassign
        taxyear=tax_prof.tax_year_id
        if taxyear:
            taxyear_id=taxyear.id
        if taxyear and taxyear.tax_payer:
            tax_payer=taxyear.tax_payer
        if taxyear and taxyear.pc_gross_income:
            pc_gross_income=(taxyear.pc_gross_income or 0)/Decimal(100)
        if taxyear and taxyear.not_exceed:
            not_exceed=taxyear.not_exceed or 0

        vals={}
        vals["B1"]=max(0,self.get_yearly_provident_fund(context=context)-10000)
        #vals["B2"]=emp.gov_pension_fund or 0
        vals["B2"]=0
        vals["B3"]=tax_prof.teacher_fund or 0
        vals["B4"]=tax_prof.old_disabled or 0
        vals["B5"]=tax_prof.old_disabled_spouse or 0
        vals["B6"]=tax_prof.severance_pay or 0
        vals["B7"]=vals["B1"]+vals["B2"]+vals["B3"]+vals["B4"]+vals["B5"]+vals["B6"]
        vals["C1"]=tax_payer
        vals["C2"]=30000 if tax_prof.spouse_filing_status in ("joint","no_income") else 0
        vals["C3a"]=15000*(tax_prof.num_child1 or 0)
        vals["C3_persons"]=tax_prof.num_child1 or 0
        vals["C3b"]=17000*(tax_prof.num_child2 or 0)
        vals["C3b_persons"]=tax_prof.num_child2 or 0
        vals["C4a"]=30000 if tax_prof.father_id_no else 0
        vals["C4b"]=30000 if tax_prof.mother_id_no else 0
        vals["C4c"]=30000 if tax_prof.spouse_father_id_no else 0
        vals["C4d"]=30000 if tax_prof.spouse_mother_id_no else 0
        vals["C5"]=tax_prof.disabled_support or 0
        vals["C6"]=tax_prof.parent_health_insurance or 0
        vals["C7a"]=tax_prof.life_insurance or 0
        vals["C8"]=min(10000,self.get_yearly_provident_fund(context=context))
        vals["C9"]=tax_prof.retirement_mutual_fund or 0
        vals["C10"]=tax_prof.long_term_equity_fund or 0
        vals["C11"]=tax_prof.interest_residence or 0
        vals["C12"]=tax_prof.other_deduct or 0
        vals["C13"]=self.get_yearly_social_security(context=context)
        vals["C14"]=vals["C1"]+vals["C2"]+vals["C3a"]+vals["C3b"]+vals["C4a"]+vals["C4b"]+vals["C4c"]+vals["C4d"]+vals["C5"]+vals["C6"]+vals["C7a"]+vals["C8"]+vals["C9"]+vals["C10"]+vals["C11"]+vals["C12"]+vals["C13"]
        vals["A1"]=self.get_yearly_income(context=context)+vals["B6"]
        vals["A2"]=vals["B7"]
        vals["A3"]=vals["A1"]-vals["A2"]
        vals["A4"]=min(pc_gross_income*vals["A3"],not_exceed) # XXX: use settings
        vals["A5"]=vals["A3"]-vals["A4"]
        vals["A6"]=vals["C14"]
        #vals["A7"]=vals["A5"]-vals["A6"]
        vals["A7"]=Decimal(vals["A5"])-vals["A6"] # XXX
        vals["A8"]=min(2*(tax_prof.education_donation or 0),Decimal(0.1)*vals["A7"])
        vals["A9"]=vals["A7"]-vals["A8"]
        vals["A10"]=min(tax_prof.other_donation or 0,Decimal(0.1)*vals["A9"])
        vals["A11"]=vals["A9"]-vals["A10"]
        vals["A12"]=get_model("hr.tax.rate").compute_tax(taxyear_id,vals["A11"])
        vals["A13"]=tax_prof.house_deduct or 0
        vals["A14"]=max(0,vals["A12"]-vals["A13"])
        vals["A15"]=tax_prof.wht_amount or 0
        vals["A16"]=vals["A14"]-vals["A15"]
        vals["A17"]=0 # XXX
        vals["A18"]=0
        vals["A19"]=0
        vals["A20"]=vals["A16"]
        vals["A21"]=0
        vals["A22"]=vals["A20"]
        context['tax_all'] = vals["A12"]
        vals["tax_month"]=self.cal_tax_month(context=context)   #vals["A12"]/period
        #from pprint import pprint
        #pprint(vals)\
        return vals

    def cal_tax_month(self,context={}):
        tax_month = get_model('hr.payslip').cal_tax(context=context)
        return tax_month

    def get_yearly_income(self,context={}):
        year_income=False
        emp_id=context.get("employee_id")
        date_to = context.get("date_to") or context.get("year_date")
        year_date_start = date_to[0:4]+"-01-01"
        year_to = date_to[0:4]
        if emp_id!='null':
            emp_id=int(emp_id)
        year_income=context.get("year_income") or 0
        date_keep=year_date_start
        obj_id = 0
        if year_income == 0:
            obj = get_model('hr.payslip').search_browse(['employee_id','=',emp_id])
            for in_id in obj:
                year_in = in_id.due_date[0:4]
                if year_to == year_in:
                    if in_id.due_date > date_keep:
                        date_keep = in_id.due_date
                        obj_id = in_id.id
            year_income = get_model('hr.payslip').get_income_year(context={'refer_id':obj_id, 'date_to':date_to, 'employee_id':emp_id, 'emp_id':emp_id})
        return year_income

    def get_yearly_provident_fund(self,context={}):
        # emp_id=context.get("employee_id")
        # if emp_id!='null':
        #     emp_id=int(emp_id)
        # emp_id = get_model("hr.employee").browse(emp_id)
        # return emp_id.year_prov
        to_date = context.get("date_to") or context.get("year_date") or 0
        to_year,to_month,to_day=to_date.split("-")
        to_year_start=to_year+"-01-01"
        to_year_end=to_year+"-12-31"
        to_month = int(to_month)
        period = 13 - to_month
        emp_id=context.get("employee_id")
        if emp_id!='null':
            emp_id=int(emp_id)
        emp = get_model("hr.employee").browse(emp_id)
        resign_date = emp.resign_date
        if not emp.prov_regis:
            return 0
        if resign_date and resign_date <= to_date:
            period = 1
        amt = 0
        payslip_template = emp.payslip_template_id
        if payslip_template:
            for line in payslip_template.lines:
                if line.payitem_id.type in ('deduct') and line.payitem_id.deduct_type=='provident':
                    amt = line.rate
        else:
            amt= 0
        amt_prov_before = 0
        obj = get_model('hr.payslip').search_browse([['employee_id','=',emp_id],['date_to','<',to_date],['due_date',">=",to_year_start],['due_date','<=',to_year_end]])
        for in_id in obj:
            for line in in_id.lines:
                if line.payitem_id.type == "deduct" and line.payitem_id.deduct_type == "provident":
                    amt_prov_before += line.rate
        obj = get_model('hr.payslip').search_browse([['employee_id','=',emp_id],['date_to','=',to_date],['due_date',">=",to_year_start],['due_date','<=',to_year_end]])
        if obj:
            for in_id in obj:
                for line in in_id.lines:
                    if line.payitem_id.type == "deduct" and line.payitem_id.deduct_type == "provident":
                        amt_prov_before += line.rate
                        period -= 1
        if period >= 1:
            amt_prov = ((amt * period) + amt_prov_before)
        else:
            amt_prov = amt_prov_before
        return amt_prov

    def get_yearly_social_security(self,context={}):
        to_date = context.get("date_to") or context.get("year_date")
        to_year,to_month,to_day=to_date.split("-")
        to_year_start=to_year+"-01-01"
        to_year_end=to_year+"-12-31"
        to_month = int(to_month)
        period = 13 - to_month
        emp_id=context.get("employee_id")
        if emp_id!='null':
            emp_id=int(emp_id)
        emp = get_model("hr.employee").browse(emp_id)
        resign_date = emp.resign_date
        if not emp.social_register:
            return 0
        if resign_date and resign_date <= to_date:
            period = 1
        amt=self.compute_thai_social(context=context)
        ss_before = 0
        obj = get_model('hr.payslip').search_browse([['employee_id','=',emp_id],['date_to','<',to_date],['due_date',">=",to_year_start],['due_date','<=',to_year_end]])
        for in_id in obj:
            for line in in_id.lines:
                if line.payitem_id.type == "deduct" and line.payitem_id.deduct_type == "thai_social":
                        ss_before += line.rate
        obj = get_model('hr.payslip').search_browse([['employee_id','=',emp_id],['date_to','=',to_date],['due_date',">=",to_year_start],['due_date','<=',to_year_end]])
        if obj:
            for in_id in obj:
                for line in in_id.lines:
                    if line.payitem_id.type == "deduct" and line.payitem_id.deduct_type == "thai_social":
                        ss_before += line.rate
                        period -= 1
        if period >= 1:
            if ss_before == 0:
                context["salary_first"] = False
                amt_sso=self.compute_thai_social(context=context)
                amt_ss = (amt_sso * (period - 1)) + amt
            else:
                amt_ss = ((amt * period) + ss_before)
        else:
            amt_ss = ss_before
        return amt_ss

    def compute_thai_tax_without(self,context={}):
        # print('compute_thai_tax ', context)
        emp_id=context.get("employee_id")
        if emp_id!='null':
            emp_id=int(emp_id)
        emp=get_model("hr.employee").browse(emp_id)
        period=context.get("period") or 12
        tax_prof=emp.tax_profile_id
        if not tax_prof and emp.tax_register:
            raise Exception("Employee code %s has not tax profile "%(emp.code))
        tax_payer=30000
        pc_gross_income=Decimal(0.4)
        not_exceed=60000
        taxyear_id=None
        # reassign
        taxyear=tax_prof.tax_year_id
        if taxyear:
            taxyear_id=taxyear.id
        if taxyear and taxyear.tax_payer:
            tax_payer=taxyear.tax_payer
        if taxyear and taxyear.pc_gross_income:
            pc_gross_income=(taxyear.pc_gross_income or 0)/Decimal(100)
        if taxyear and taxyear.not_exceed:
            not_exceed=taxyear.not_exceed or 0

        vals={}
        vals["B1"]=max(0,self.get_yearly_provident_fund(context=context)-10000)
        #vals["B2"]=emp.gov_pension_fund or 0
        vals["B2"]=0
        vals["B3"]=tax_prof.teacher_fund or 0
        vals["B4"]=tax_prof.old_disabled or 0
        vals["B5"]=tax_prof.old_disabled_spouse or 0
        vals["B6"]=tax_prof.severance_pay or 0
        vals["B7"]=vals["B1"]+vals["B2"]+vals["B3"]+vals["B4"]+vals["B5"]+vals["B6"]
        vals["C1"]=tax_payer
        vals["C2"]=30000 if tax_prof.spouse_filing_status in ("joint","no_income") else 0
        vals["C3a"]=15000*(tax_prof.num_child1 or 0)
        vals["C3_persons"]=tax_prof.num_child1 or 0
        vals["C3b"]=17000*(tax_prof.num_child2 or 0)
        vals["C3b_persons"]=tax_prof.num_child2 or 0
        vals["C4a"]=30000 if tax_prof.father_id_no else 0
        vals["C4b"]=30000 if tax_prof.mother_id_no else 0
        vals["C4c"]=30000 if tax_prof.spouse_father_id_no else 0
        vals["C4d"]=30000 if tax_prof.spouse_mother_id_no else 0
        vals["C5"]=tax_prof.disabled_support or 0
        vals["C6"]=tax_prof.parent_health_insurance or 0
        vals["C7a"]=tax_prof.life_insurance or 0
        vals["C8"]=min(10000,self.get_yearly_provident_fund(context=context))
        vals["C9"]=tax_prof.retirement_mutual_fund or 0
        vals["C10"]=tax_prof.long_term_equity_fund or 0
        vals["C11"]=tax_prof.interest_residence or 0
        vals["C12"]=tax_prof.other_deduct or 0
        vals["C13"]=self.get_yearly_social_security(context=context)
        vals["C14"]=vals["C1"]+vals["C2"]+vals["C3a"]+vals["C3b"]+vals["C4a"]+vals["C4b"]+vals["C4c"]+vals["C4d"]+vals["C5"]+vals["C6"]+vals["C7a"]+vals["C8"]+vals["C9"]+vals["C10"]+vals["C11"]+vals["C12"]+vals["C13"]
        vals["A1"]=self.get_yearly_income(context=context)+vals["B6"]
        vals["A2"]=vals["B7"]
        vals["A3"]=vals["A1"]-vals["A2"]
        vals["A4"]=min(pc_gross_income*vals["A3"],not_exceed) # XXX: use settings
        vals["A5"]=vals["A3"]-vals["A4"]
        vals["A6"]=vals["C14"]
        #vals["A7"]=vals["A5"]-vals["A6"]
        vals["A7"]=Decimal(vals["A5"])-vals["A6"] # XXX
        vals["A8"]=min(2*(tax_prof.education_donation or 0),Decimal(0.1)*vals["A7"])
        vals["A9"]=vals["A7"]-vals["A8"]
        vals["A10"]=min(tax_prof.other_donation or 0,Decimal(0.1)*vals["A9"])
        vals["A11"]=vals["A9"]-vals["A10"]
        vals["A12"]=get_model("hr.tax.rate").compute_tax(taxyear_id,vals["A11"])
        vals["A13"]=tax_prof.house_deduct or 0
        vals["A14"]=max(0,vals["A12"]-vals["A13"])
        vals["A15"]=tax_prof.wht_amount or 0
        vals["A16"]=vals["A14"]-vals["A15"]
        vals["A17"]=0 # XXX
        vals["A18"]=0
        vals["A19"]=0
        vals["A20"]=vals["A16"]
        vals["A21"]=0
        vals["A22"]=vals["A20"]
        # context['tax_all'] = vals["A12"]
        # vals["tax_month"]=self.cal_tax_month(context=context)   #vals["A12"]/period
        #from pprint import pprint
        #pprint(vals)
        return vals

PayItem.register()
