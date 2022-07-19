from netforce.model import get_model
from netforce import migration
from netforce import utils
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="share.condition"
    _version="3.1.0"

    def migrate(self):
        db=get_connection()
        db.execute("UPDATE share_access SET condition=domain WHERE condition IS NULL")

Migration.register()
