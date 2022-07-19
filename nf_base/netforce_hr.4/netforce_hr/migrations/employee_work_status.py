from netforce.database import get_connection
from netforce import migration

class Migration(migration.Migration):
    _name="hr.employee.leave.status"
    _version="2.12.0"

    def migrate(self):
        print("Upate work status for employee ...")
        db=get_connection()
        db.execute("update hr_leave as l set employee_work_status = (select x.work_status from hr_employee as x where id=l.employee_id)")

Migration.register()

