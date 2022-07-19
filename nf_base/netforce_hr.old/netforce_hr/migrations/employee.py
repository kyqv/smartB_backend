from netforce.model import get_model
from netforce import migration
from netforce.database import get_connection
from netforce.access import get_active_user, set_active_user

class Migration(migration.Migration):
    _name="hr.employee"
    _version="2.12.0"

    def migrate(self):
        user_id=get_active_user()
        set_active_user(1)
        db=get_connection()
        for emp in get_model("hr.employee").search_browse([]):
            prov_open_date=emp.prov_open_date 
            if prov_open_date:
                emp.write({
                    'note': prov_open_date,
                })
            db.execute("alter table hr_employee drop column prov_open_date")
        set_active_user(user_id)

Migration.register()

