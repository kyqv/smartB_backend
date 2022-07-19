import time

from netforce.model import get_model
from netforce import migration
from netforce.access import set_active_user, get_active_user, set_active_company, get_active_company

class Migration(migration.Migration):
    _name="add.tax.profile"
    _version="2.12.0"

    def migrate(self):
        company_id=get_active_company()
        user_id=get_active_user()
        set_active_user(1)
        set_active_company(1)
        res=get_model("hr.tax.year").search([])
        if not res:
            tax_year_id=get_model("hr.tax.year").create({'name': time.strftime("%Y")})
            tax_rate_ids=get_model('hr.tax.rate').search([])
            if tax_rate_ids:
                for taxrate in get_model('hr.tax.rate').browse(tax_rate_ids):
                    taxrate.write({
                        'tax_year_id': tax_year_id,
                    })
        
            else:
                tax_year=get_model('hr.tax.year').browse(tax_year_id)
                tax_year.write({
                    'tax_rates': [
                        ('create',{'min_income': 0, 'max_income': 150000, 'rate': 0}),
                        ('create',{'min_income': 150001, 'max_income': 500000, 'rate': 10}),
                        ('create',{'min_income': 500001, 'max_income': 1000000, 'rate': 20}),
                        ('create',{'min_income': 1000001, 'max_income': 4000000, 'rate':30}),
                        ('create',{'min_income': 4000001, 'max_income': 0, 'rate': 0}),
                    ],
                })
        
        for emp in get_model("hr.employee").search_browse([['work_status','=','working']]):
            res=get_model('hr.tax.profile').search([['employee_id','=',emp.id]])
            if not res:
                vals={
                    'employee_id': emp.id,
                    "spouse_first_name": emp.spouse_first_name,
                    "spouse_last_name": emp.spouse_last_name,
                    "spouse_title": emp.spouse_title,
                    "spouse_birth_date": emp.spouse_birth_date,
                    "spouse_tax_no": emp.spouse_tax_no,
                    "spouse_status": emp.spouse_status,
                    "spouse_filing_status": emp.spouse_filing_status,
                    "num_child1": emp.num_child1,
                    "num_child2": emp.num_child2,
                    "social_calc_method": emp.social_calc_method,
                    "prov_fund_no": emp.prov_fund_no,
                    "prov_open_date": emp.prov_open_date,
                    "prov_rate_employer": emp.prov_rate_employer,
                    "prov_rate_employee": emp.prov_rate_employee,
                    "gov_pension_fund": emp.gov_pension_fund,
                    "teacher_fund": emp.teacher_fund,
                    "old_disabled": emp.old_disabled,
                    "old_disabled_spouse": emp.old_disabled_spouse,
                    "severance_pay": emp.severance_pay,
                    "education_donation": emp.education_donation,
                    "other_donation": emp.other_donation,
                    "house_deduct": emp.house_deduct,
                    "wht_amount": emp.wht_amount,
                    "father_id_no": emp.father_id_no,
                    "mother_id_no": emp.mother_id_no,
                    "spouse_father_id_no": emp.spouse_father_id_no,
                    "spouse_mother_id_no": emp.spouse_mother_id_no,
                    "disabled_support": emp.disabled_support,
                    "parent_health_insurance": emp.parent_health_insurance,
                    "life_insurance": emp.life_insurance,
                    "retirement_mutual_fund": emp.retirement_mutual_fund,
                    "long_term_equity_fund": emp.long_term_equity_fund,
                    "interest_residence": emp.interest_residence,
                    "other_deduct": emp.other_deduct,
                }
                get_model('hr.tax.profile').create(vals)
                
        set_active_user(user_id)
        set_active_company(company_id)
    

Migration.register()

