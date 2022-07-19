from netforce.model import Model, fields

class TaxProfile(Model):
    _name="hr.tax.profile"
    _string="Tax Profile"
    _name_field="tax_year_id"

    _fields={
        'tax_year_id': fields.Many2One("hr.tax.year","Tax Year",required=True,search=True),
        'employee_id': fields.Many2One("hr.employee","Employee",required=True,search=True),
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
        "comments":fields.One2Many("message","related_id","Comments"),
    }
    

TaxProfile.register()
