from netforce.model import get_model
from netforce import migration
from netforce.access import set_active_user, get_active_user, set_active_company, get_active_company

class Migration(migration.Migration):
    _name="improve.payslip"
    _version="2.12.0"

    def migrate(self):
        company_id=get_active_company()
        user_id=get_active_user()
        set_active_user(1)
        set_active_company(1)
        for payslip in get_model("hr.payslip").search_browse([]):
            vals={}
            if not payslip.state:
                vals['state']='draft'
            if not payslip.date_from and payslip.date_to:
                y,m,d=payslip.date_to.split("-")
                vals['date_from']='%s-%s-%s'%(y,m,'01')
            if payslip.due_date:
                vals['date_to']=payslip.due_date
            payslip.write(vals)

        for payrun in get_model("hr.payrun").search_browse([]):
            if not payrun.state:
                payrun.write({
                    'state': 'draft',
                })
        set_active_user(user_id)
        set_active_company(company_id)

Migration.register()

