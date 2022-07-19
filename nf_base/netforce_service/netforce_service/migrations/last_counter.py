from netforce.model import get_model
from netforce import migration
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="service.last_counter"
    _version="1.161.0"

    def migrate(self):
        db=get_connection()
        db.execute("alter table service_item drop column last_counter") # XXX: because change to int

Migration.register()
