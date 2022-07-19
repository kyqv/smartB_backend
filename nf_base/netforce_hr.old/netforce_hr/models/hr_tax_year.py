from netforce.model import Model, fields

class TaxYear(Model):
    _name="hr.tax.year"
    _string="Tax Year"
    _fields={
        "name": fields.Char("Name", required=True,search=True),
        "tax_rates": fields.One2Many("hr.tax.rate","tax_year_id","Tax Rates"),
        "comments":fields.One2Many("message","related_id","Comments")
    }

TaxYear.register()
