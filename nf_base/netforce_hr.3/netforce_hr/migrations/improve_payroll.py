from netforce.model import get_model
from netforce import migration
from netforce.access import set_active_user, get_active_user

class Migration(migration.Migration):
    _name="improve.payroll"
    _version="2.12.0"

    def migrate(self):
        user_id=get_active_user()
        set_active_user(1)
        for payslip in get_model("hr.payslip").search_browse([]):
            if not payslip.state:
                payslip.write({
                    'state': 'draft',
                })
        for payrun in get_model("hr.payrun").search_browse([]):
            if not payrun.state:
                payrun.write({
                    'state': 'draft',
                })
        set_active_user(user_id)

Migration.register()

