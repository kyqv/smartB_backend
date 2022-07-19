import time

from netforce.model import get_model
from netforce import migration
from netforce.access import set_active_user, get_active_user, set_active_company, get_active_company
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="add.payslip.template"
    _version="2.12.0"

    def migrate(self):
        company_id=get_active_company()
        user_id=get_active_user()
        set_active_user(1)
        set_active_company(1)
        currencys=get_model('currency').search_browse([])
        currency_id=None
        currency_rate=1
        if currencys:
           currency_id=currencys[0].id
           currency_rate=currencys[0].sell_rate or 1
        db=get_connection()
        res=db.query("select id, profile_id from hr_employee")
        print("res ", res)
        for r in res:
            employee_id=r['id']
            profile_id=r['profile_id']
            employee=get_model('hr.employee').browse(employee_id)
            vals={}
            if not employee.payslip_template_id and profile_id:
                vals.update({
                    'employee_id': employee_id,
                    'payitem_profile_id': profile_id,
                    'lines': [],
                })
                profile=get_model("hr.payitem.profile").browse(profile_id)
                ctx={
                    'employee_id': employee.id,
                }
                for item in profile.pay_items:
                    qty,rate=item.compute(context=ctx)
                    vals['lines'].append(('create',{
                        'payitem_id': item.id,
                        'currency_id': currency_id,
                        'currency_rate': currency_rate,
                        'qty': qty,
                        'rate': rate,
                        'amount': qty*rate*currency_rate,
                    }))
                if vals:
                    new_tmpl_id=get_model('hr.payslip.template').create(vals)
                employee.write({
                    'payslip_template_id': new_tmpl_id,
                })
        set_active_user(user_id)
        set_active_company(company_id)
    

Migration.register()

