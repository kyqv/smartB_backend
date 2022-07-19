from netforce import migration
from netforce.database import get_connection

class attendance_add_field_mode(migration.Migration):
    """ remove field attendance_id of int to be char to be more understanable """

    _name="attendance.add.field.mode"
    _version="2.12.0"

    def migrate(self):
        # ./run.py -m 2.11.0
        db=get_connection()

        db.execute("update hr_attendance set mode='manual' where mode is null")

attendance_add_field_mode.register()
