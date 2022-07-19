import time

from netforce.model import get_model
from netforce import migration
from netforce.access import set_active_user, get_active_user

class Migration(migration.Migration):
    _name="improve.tax"
    _version="2.12.0"

    def migrate(self):
        user_id=get_active_user()
        set_active_user(1)
        set_active_user(user_id)
        taxyear_ids=get_model('hr.tax.year').search([])
        if not taxyear_ids:
            yearnow=time.strftime("%Y")
            lines=[]
            pst=get_model('hr.payroll.settings').browse(1)
            for taxrate in pst.tax_rates:
                vals={
                    "sequence": taxrate.sequence,
                    "min_income": taxrate.min_income,
                    "max_income": taxrate.max_income,
                    "rate": taxrate.rate,
                }
                lines.append(('create', vals))
            get_model('hr.tax.year').create({
                'name': yearnow,
                'tax_rates': lines,
            })
            print('tax year %s is created'%yearnow)


Migration.register()

