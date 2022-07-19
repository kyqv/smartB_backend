from netforce import migration
from netforce.access import set_active_user, get_active_user, set_active_company, get_active_company
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="improve.payitem"
    _version="2.12.0"

    def migrate(self):
        company_id=get_active_company()
        user_id=get_active_user()
        set_active_user(1)
        set_active_company(1)
        db=get_connection()
        db.execute("""
            update hr_payitem set include_tax=true where type!='tax';
        """)
        set_active_user(user_id)
        set_active_company(company_id)

Migration.register()

