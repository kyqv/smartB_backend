import time

from netforce.model import Model, fields, get_model
from netforce import database
from netforce.access import get_active_company
from decimal import *

class Employee(Model):
    _name="hr.employee"
    _string="Employee"
    _name_field="first_name" # XXX
    _multi_company=True
    _key=["code"]
    _export_name_field="code"

    def get_ytd(self,ids,context={}):
        yearnow=time.strftime("%Y")
        year=context.get('year')
        date_from=context.get('date_from') #begin of year
        all_vals={
            'year_income': 0,
            'year_deduct': 0,
            'year_tax': 0,
            'year_soc': 0,
            'year_prov': 0,
            'year_acc_prov': 0,
        }
        for obj in self.browse(ids):
            if not year:
                year=yearnow
                if obj.tax_profile_id:
                    year=obj.tax_profile_id.tax_year_id.name
            for payslip in obj.payslips:
                if not payslip.date_from:
                    continue
                payslip_year=payslip.date_from[0:4]
                if year != payslip_year:
                    continue
                if date_from:
                    if payslip.date_from > date_from: #XXX equal ?
                        continue
                #all_vals['year_income']+=payslip.amount_net or 0
                for line in payslip.lines:
                    item=line.payitem_id
                    if item.type in ('wage','allow'):
                        all_vals['year_income']+=line.amount or 0
                    elif item.type in ('deduct'):
                        if item.deduct_type=='provident':
                            all_vals['year_prov']+=line.amount or 0
                        elif item.deduct_type=='thai_social':
                            all_vals['year_soc']+=line.amount or 0
                        else:
                            all_vals['year_deduct']+=line.amount or 0
                    elif item.type in ('tax'):
                        all_vals['year_tax']+=line.amount or 0
            return all_vals

    def _get_ytd(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            res[obj.id]=obj.get_ytd()
        return res

    def _get_tax_profile(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            for tax_profile in obj.tax_profiles:
                res[obj.id]=tax_profile.id
        return res

    def _get_leaves(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            res[obj.id]={
            }
        return res

    def _get_report_address(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            res[obj.id]=' '.join([a for a in (
                obj.depart_name or '',
                obj.depart_room_number or '',
                obj.depart_stage or '',
                obj.depart_village or '',
                obj.depart_number or '',
                obj.depart_sub_number or '',
                obj.depart_soi or '',
                obj.depart_road or '',
                obj.depart_sub_district or '',
                obj.depart_district or '',
                obj.depart_province or '',
                obj.depart_zip or '',
                #obj.depart_tel and 'Tel.: %s'%obj.depart_tel or '',
                ) if a])
        return res

    def _get_currency_rate(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            curr_rate=1
            if obj.currency_id:
                curr_rate=obj.currency_id.sell_rate or 1
            res[obj.id]=curr_rate
        return res

    _fields={
        "code": fields.Char("Employee Code",search=True),
        "department_id": fields.Many2One("hr.department","Department",search=True),
        "title": fields.Selection([["mr","Mr."],["mrs","Mrs."],["miss","Miss"],["ms","Ms."]],"Title"),
        "first_name": fields.Char("First Name",required=True,search=True,translate=True),
        "last_name": fields.Char("Last Name",required=True,search=True,translate=True),
        "hire_date": fields.Date("Hire Date",required=True),
        "work_status": fields.Selection([["working","Working"],["dismissed","Dismissed"],["resigned","Resigned"],["died","Died"]],"Work Status"),
        "work_type": fields.Selection([["monthly","Monthly"],["daily","Daily"],["hourly","Job"]],"Work Type"),
        "resign_date": fields.Date("Resign Date"),
        "position": fields.Char("Position",search=True),
        "birth_date": fields.Date("Birth Date"),
        "age": fields.Integer("Age",function="get_age"),
        "gender": fields.Selection([["male","Male"],["female","Female"]],"Gender"),
        "marital_status": fields.Selection([["single","Single"],["married","Married"],["divorced","Divorced"],["widowed","Widowed"]],"Marital Status"),
        "addresses": fields.One2Many("address","employee_id","Address"),
        "id_no": fields.Char("ID Card No."),
        "drive_license_type": fields.Selection([["car","Car"],['motorcycle','Motorcycle']],"Driving License"),
        "drive_license_no": fields.Char("Driving License No."),
        "country_id": fields.Many2One("country","Country"),
        "bank_account": fields.Char("Bank Account"),
        "salary": fields.Decimal("Salary"),
        "picture": fields.File("Picture"),
        "tax_no": fields.Char("Taxpayer ID No."),
        "tax_register": fields.Boolean("Register Tax"),
        "spouse_first_name": fields.Char("Spouse First Name"),
        "spouse_last_name": fields.Char("Spouse Last Name"),
        "spouse_title": fields.Selection([["mr","Mr."],["ms","Ms."]],"Spouse Title"),
        "spouse_birth_date": fields.Date("Spouse Birth Date"),
        "spouse_tax_no": fields.Char("Spouse Tax ID No"),
        "spouse_status": fields.Selection([["married","Married existed throughout this tax year"],["married_new","Married during this tax year"],["divorced","Divorced during tax year"],["deceased","Deceased during tax year"]],"Spouse Status"),
        "spouse_filing_status": fields.Selection([["joint","Has income and file joint return"],["separate","Has income and file separate tax return"],["no_income","Has no income"]],"Spouse Filing Status"),
        "num_child1": fields.Integer("No. of Children #1 (C3)"),
        "num_child2": fields.Integer("No. of Children #2 (C3)"),
        "social_no": fields.Char("Social No."),
        "social_register": fields.Boolean("Register Soc. Secur."),
        "social_calc_method": fields.Selection([["regular","Regular Rate"],["none","Not Participate"],["special","Special Rate"]],"Calc. Method"),
        "prov_fund_no": fields.Char("Prov. Fund No."),
        #"prov_open_date": fields.Date("Opened Prov. Fund AC Date"),
        "prov_open_date": fields.Char("Opened Prov. Fund AC Date"),
        "prov_rate_employer": fields.Decimal("Employer Contribution (%)"),
        "prov_rate_employee": fields.Decimal("Employee Contribution (%)"),
        "prov_regis": fields.Boolean("Register Provident"),
        "gov_pension_fund": fields.Decimal("Gov. Pension Fund Amount (B2)"),
        "teacher_fund": fields.Decimal("Teacher Aid Fund Amount (B3)"),
        "old_disabled": fields.Decimal("Older than 65 or disabled (personal, B4)"),
        "old_disabled_spouse": fields.Decimal("Older than 65 or disabled (spouse, B5)"),
        "severance_pay": fields.Decimal("Severance Pay (B6)"),
        "education_donation": fields.Decimal("Education Donations (A8)"),
        "other_donation": fields.Decimal("Other Donations (A10)"),
        "house_deduct": fields.Decimal("Exemption for home buyer (A13)"),
        "wht_amount": fields.Decimal("Withholding Tax Amount (A15)"),
        "father_id_no": fields.Char("Father ID No. (C4)"),
        "mother_id_no": fields.Char("Mother ID No. (C4)"),
        "spouse_father_id_no": fields.Char("Father of spouse ID No. (C4)"),
        "spouse_mother_id_no": fields.Char("Mother of spouse ID No. (C4)"),
        "disabled_support": fields.Decimal("Disabled person support (C5)"),
        "parent_health_insurance": fields.Decimal("Parent Health Insurance (C6)"),
        "life_insurance": fields.Decimal("Life Insurance (C7)"),
        "retirement_mutual_fund": fields.Decimal("Retirement Mutual Fund (C9)"),
        "long_term_equity_fund": fields.Decimal("Long Term Equity Fund (C10)"),
        "interest_residence": fields.Decimal("Interest paid for residence (C11)"),
        "other_deduct": fields.Decimal("Other Deductions (C12)"),
        "comments": fields.One2Many("message","related_id","Comments"),
        "active": fields.Boolean("Active"),
        "time_in": fields.DateTime("Last Sign In",function="get_attend",function_multi=True),
        "time_out": fields.DateTime("Last Sign Out",function="get_attend",function_multi=True),
        "attend_state": fields.Selection([["absent","Absent"],["present","Present"]],"Status",function="get_attend",function_multi=True),
        "user_id": fields.Many2One("base.user","User",search=True),
        "payslips": fields.One2Many("hr.payslip","employee_id","Payslips"),
        "documents": fields.One2Many("document","related_id","Documents"),
        "phone": fields.Char("Mobile Phone",search=True),
        "approver_id": fields.Many2One("base.user","Approver"),
        "company_id": fields.Many2One("company","Company"),
        "leave_types": fields.Many2Many("hr.leave.type","Leave Types"),
        "attendance_code": fields.Char("Attendance Code"),
        "email": fields.Char("Email",search=True),
        'profile_id': fields.Many2One("hr.payitem.profile", "Pay Item Profile"),
        'schedule_id': fields.Many2One("hr.schedule", "Working Schedule"),
        'leaves': fields.One2Many('hr.leave','employee_id','Leaves'),
        'tax_profiles': fields.One2Many('hr.tax.profile','employee_id','Tax Profiles'),
        'tax_profile_id': fields.Many2One('hr.tax.profile','Current Tax Profile',function="_get_tax_profile"),
        'year_income': fields.Decimal('Incomes',function="_get_ytd", function_multi=True),
        'year_deduct': fields.Decimal('Deductions',function="_get_ytd", function_multi=True),
        'year_tax': fields.Decimal('Income Tax',function="_get_ytd", function_multi=True),
        'year_soc': fields.Decimal('Social Security',function="_get_ytd", function_multi=True),
        'year_prov': fields.Decimal('Provident Fund',function="_get_ytd", function_multi=True),
        'year_acc_prov': fields.Decimal('Year Acc Provident Fund',function="_get_ytd", function_multi=True),
        'name_th': fields.Char("Employee First Name (TH)"),
        'name_last_th': fields.Char("Employee Last Name (TH)"),
        # report address thai
        'depart_room_number': fields.Char("Room No."),
        'depart_stage':fields.Char("Stage"),
        'depart_village': fields.Char("Village"),
        'depart_name': fields.Char("Department Name"),
        'depart_number': fields.Char("Department No."),
        'depart_sub_number': fields.Char("Dpt Sub No."),
        'depart_soi': fields.Char("Soi"),
        'depart_road': fields.Char("Road"),
        'depart_district': fields.Char("District"),
        'depart_sub_district': fields.Char("Sub District"),
        'depart_province': fields.Char("Province"),
        'depart_zip': fields.Char("Zip"),
        'depart_tel': fields.Char("Tel."),
        'report_address_txt': fields.Text("Address Report",function="_get_report_address"),
        'note': fields.Text("Note"),
        'payslip_template_id': fields.Many2One("hr.payslip.template",'Payslip Template'),
        "sellers": fields.One2Many("seller","employee_id","Sellers"),
    }

    def _get_code(self,context={}):
        while 1:
            code=get_model("sequence").get_number("employee")
            if not code:
                return None
            res=self.search([["code","=",code]])
            if not res:
                return code
            get_model("sequence").increment("employee")

    _defaults={
        "active": True,
        "code": _get_code,
        "company_id": lambda *a: get_active_company(),
        'social_register': True,
        'hire_date': lambda *a: time.strftime("%Y-%m-%d"),
        'tax_register': True,
        'prov_regis': True,
        'work_type': 'monthly',
        "work_status": "working",
    }
    _order="code,first_name,last_name"

    def name_get(self,ids,context={}):
        vals=[]
        for obj in self.browse(ids):
            if obj.first_name:
                name=obj.first_name+" "+obj.last_name
            else:
                name=obj.last_name
            if obj.code:
                name+=" [%s]"%obj.code
            vals.append((obj.id,name))
        return vals

    def name_search(self,name,condition=[],limit=None,context={}):
        cond=[["or",["first_name","ilike","%"+name+"%"],["last_name","ilike","%"+name+"%"],["code","ilike","%"+name+"%"]],condition]
        ids=self.search(cond,limit=limit)
        return self.name_get(ids,context)

    def get_age(self,ids,context={}):
        vals={}
        cr_year=int(time.strftime('%Y'))
        cr_month=int(time.strftime('%m'))
        cr_date = int(time.strftime('%d'))
        for obj in self.browse(ids):
            if obj.birth_date:
                y = int(obj.birth_date[0:4])
                age = cr_year - y
                m=int(obj.birth_date[5:7])
                if m > cr_month:
                    age -= 1
                elif m == cr_month:
                    d = int(obj.birth_date[8:10])
                    if d > cr_date:
                        age -= 1
                    else:
                        age = age
                #m=m-cr_month
            else:
                age=0
            vals[obj.id]=age
        return vals

    def get_attend(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            #user_id=obj.user_id.id
            #if user_id:
                #db=database.get_connection()
                #res=db.get("SELECT MAX(time) AS time_in FROM hr_attendance WHERE user_id=%s AND action='sign_in'",user_id)
                #time_in=res.time_in
                #res=db.get("SELECT MAX(time) AS time_out FROM hr_attendance WHERE user_id=%s AND action='sign_out'",user_id)
                #time_out=res.time_out
            #else:
                #time_in=None
                #time_out=None
            db=database.get_connection()
            res=db.get("SELECT MAX(time) AS time_in FROM hr_attendance WHERE employee_id=%s AND action='sign_in'",obj.id)
            time_in=res.time_in
            res=db.get("SELECT MAX(time) AS time_out FROM hr_attendance WHERE employee_id=%s AND action='sign_out'",obj.id)
            time_out=res.time_out
            if time_in:
                if time_out and time_out>time_in:
                    state="absent"
                else:
                    today=time.strftime("%Y-%m-%d")
                    if time_in.startswith(today):
                        state="present"
                    else:
                        state="absent"
                    # should not show timeout of anotherday
                    #if not time_out.startswith(today):
                        #time_out=None
            else:
                state="absent"
            vals[obj.id]={
                "time_in": time_in,
                "time_out": time_out,
                "attend_state": state,
            }
        return vals

    def get_address(self,ids,context={}):
        obj=self.browse(ids)[0]
        if not obj.addresses:
            return ""
        addr=obj.addresses[0]
        res=addr.get_address_text()
        return res[addr.id]

    def onchange_num_child(self,context={}):
        data=context["data"]
        setting=get_model("hr.payroll.settings").browse(1)
        child_alw_limit=setting.child_alw_limit or 0
        child_total=(data['num_child1'] or 0)+(data['num_child2'] or 0)
        if child_alw_limit and child_total > child_alw_limit:
            data['num_child1']=0
            data['num_child2']=0
        return data
    
    def write(self,ids,vals,**kw):
        obj=self.browse(ids)[0]
        if 'work_status' in vals.keys():
            if not vals.get("resign_date"):
                vals['resign_date']=time.strftime("%Y-%m-%d")
        code = obj.code
        #salary = vals.get("salary")
        if code:
            res=self.search([['code','=',code]])
            if res:
                emp=self.browse(res[0])
                temp = emp.payslip_template_id
                if vals.get("prov_rate_employee") or vals.get("salary"):
                    salary = vals.get("salary")
                    prov_rate = vals.get("prov_rate_employee") or obj.prov_rate_employee
                    if salary:
                        prov_amt = salary * (prov_rate or 0)/100
                    else:
                        prov_amt = obj.salary * (prov_rate or 0)/100
                if temp:
                    for line in temp.lines:
                        item = line.payitem_id
                        if item.type == "wage" and item.wage_type == "salary":
                            if vals.get("salary"):
                                line.write({
                                    'rate': salary,
                                })
                        if item.type == "deduct" and item.deduct_type=="provident":
                            if vals.get("prov_rate_employee") or vals.get("salary"):
                                line.write({
                                    'rate': prov_amt,
                                })
                        if item.type == "contrib" and item.contrib_type=="prov":
                            if vals.get("prov_rate_employee") or vals.get("salary"):
                                prov_amt_acc = prov_amt *2
                                line.write({
                                    'rate': prov_amt_acc,
                                })
        super().write(ids,vals,**kw)
    
    def onchange_work_status(self,context={}):
        data=context['data']
        if data['work_status']=='resigned':
            data['resign_date']=time.strftime("%Y-%m-%d")
        return data

    def get_income(self,ids,context={}):
        obj=self.browse(ids)[0]
        date_from=context.get('date_from')
        date_to=context.get('date_to')
        income=0
        if date_from and date_to:
            for payslip in obj.payslips:
                if payslip.date_from >= date_from and payslip.date_to < date_to:
                    for line in payslip.lines:
                        item=line.payitem_id
                        if not item.include_tax:
                            continue 
                        if item.type in ('wage','allow'):
                            income+=line.amount
        return income

    def onchange_gender(self,context={}):
        data=context['data']
        if data['title'] == 'mr':
            data['gender'] = 'male'
        elif data['title'] in ('mrs','miss','ms'):
            data['gender'] = 'female'
        return data

    def onchange_id_no(self,context={}):
        data=context['data']
        if data['id_no'] != "":
            data['social_no'] = data['id_no']
            data['tax_no'] = data['id_no']
        else:
            data['social_no'] = ""
            data['tax_no'] = ""
        return data

    def calc_overtime(self,ids,date_from=None,date_to=None,context={}):
        obj=self.browse(ids[0])
        cond=[["date",">=",date_from],["date","<=",date_to],["state","=","approved"],["employee_id","=",obj.id]]
        days={}
        for leave in get_model("hr.leave").search_browse(cond):
            rate=leave.leave_type_id.day_rate
            if not rate:
                continue
            qty=Decimal(leave.days_requested or 0)
            days.setdefault(rate,0)
            days[rate]+=qty
        return days

Employee.register()
