import time

from netforce.model import Model, fields, get_model
from netforce.access import get_active_user, get_active_company

class TaxProfile(Model):
    _name="hr.tax.profile"
    _string="Tax Profile"
    _multi_company=True
    _key=['employee_id','tax_year_id']
    
    def _get_name(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            emp_name=obj.employee_id.name_get()[0][1]
            print('emp_name ', emp_name)
            tax_year=obj.tax_year_id.name or ''
            res[obj.id]='%s - %s'%(emp_name,tax_year)
        return res

    _fields={
        'name': fields.Char("Name",function="_get_name"),
        'employee_id': fields.Many2One("hr.employee","Employee",required=True,search=True),
        'tax_year_id': fields.Many2One("hr.tax.year","Tax Year",required=True,search=True),
        'income_accum': fields.Decimal("Income Accum."),
        'deduction_accum': fields.Decimal("Deduction Accum."),
        'sso_accum': fields.Decimal("Secial Security Accum."),
        'provident_accum': fields.Decimal("Provident Fund Accum."),
        'tax_accum': fields.Decimal("Tax Accum."),
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
        "prov_open_date": fields.Char("Opened Prov. Fund A/C Date"),
        "prov_rate_employer": fields.Decimal("Employer Contribution (%)"),
        "prov_rate_employee": fields.Decimal("Employee Contribution (%)"),
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
        'company_id': fields.Many2One("company","Company"),
    }
    
    def get_tax_year(self,context={}):
        yearnow=time.strftime("%Y")
        year_id=None
        for tax_year_id in get_model("hr.tax.year").search([['name','=',yearnow]]):
            year_id=tax_year_id
        return year_id

    def get_employee(self,context={}):
        user_id=get_active_user()
        employee_id=None
        for emp_id in get_model("hr.employee").search([['user_id','=',user_id]]):
            employee_id=emp_id
        return employee_id

    _defaults={
        'tax_year_id': get_tax_year,
        'employee_id': get_employee,
        'company_id': lambda *a: get_active_company(),
    }

    def onchange_num_child(self,context={}):
        data=context["data"]
        setting=get_model("hr.payroll.settings").browse(1)
        child_alw_limit=setting.child_alw_limit or 0
        child_total=(data['num_child1'] or 0)+(data['num_child2'] or 0)
        if child_alw_limit and child_total > child_alw_limit:
            data['num_child1']=0
            data['num_child2']=0
        return data

    def create(self,vals,**kw):
        new_id=super().create(vals,**kw)
        self.function_store([new_id])
        return new_id

    def write(self,ids,vals,**kw):
        if 'num_child2' in vals.keys():
            if not vals['num_child2']:
                vals['num_child2']=0
        if 'num_child1' in vals.keys():
            if not vals['num_child1']:
                vals['num_child1']=0
        self.function_store(ids)
        super().write(ids,vals,**kw)

TaxProfile.register()
