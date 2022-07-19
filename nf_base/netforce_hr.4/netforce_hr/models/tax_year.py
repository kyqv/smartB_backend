import time

from netforce.model import Model, fields

class TaxYear(Model):
    _name="hr.tax.year"
    _string="Tax Year"
    _fields={
        'name': fields.Char("Name", required=True),
        'tax_payer': fields.Decimal("Tax Payer"),
        'pc_gross_income': fields.Decimal("% Of Gross Income"),
        'not_exceed': fields.Decimal("Not Exceeding"),
        "tax_rates": fields.One2Many("hr.tax.rate","tax_year_id","Tax Rates"),
        "comments": fields.One2Many("message","related_id","Comments"),
        #TODO add another configuration
    }

    def get_tax_rates(self,context={}):
        rates=[
            {'min_income': 0, 'max_income': 150000, 'rate': 0},
            {'min_income': 150001, 'max_income': 500000, 'rate': 10},
            {'min_income': 500001, 'max_income': 1000000, 'rate': 20},
            {'min_income': 1000001, 'max_income': 4000000, 'rate':30},
            {'min_income': 4000001, 'max_income': 0, 'rate': 0},
        ]
        return rates

    _defaults={
        'name': lambda *a: time.strftime("%Y"),    
        'tax_rates': get_tax_rates,
        'tax_payer': 30000,
        'pc_exceed': 40,
        'not_exceed': 60000,
    }
    
    def copy(self,ids,context={}):
        obj=self.browse(ids)[0]
        tax_rates=[]
        for tax_rate in obj.tax_rates:
            tax_rates.append(('create',{
                    'min_income': tax_rate.min_income,
                    'max_income': tax_rate.max_income,
                    'rate': tax_rate.rate,
                }))
        vals={
            'name': time.strftime("%Y"),
            'tax_rates': tax_rates,
        }
        new_id=self.create(vals)
        return {
            'next': {
                'name': 'tax_year',
                'mode': 'form',
                'active_id': new_id,
            },
            'flash': 'Copy successfully',
        }

TaxYear.register()
