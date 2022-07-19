from netforce import migration
from netforce.database import get_connection

class attendance_id_to_code(migration.Migration):
    """ remove field attendance_id of int to be char to be more understanable """

    _name="attendance.id.to.code"
    _version="2.12.0"

    def migrate(self):
        # ./run.py -m 2.11.0
        db=get_connection()

        res = db.query("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='hr_employee' and column_name='attendance_id';
                    """)
        if res:
            db.execute("update hr_employee set attendance_code=attendance_id")
            db.execute("alter table hr_employee drop column attendance_id")

        print("Migrate : attendance_id to use code  done !")

attendance_id_to_code.register()
