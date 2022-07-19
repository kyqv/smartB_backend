from netforce import migration
from netforce.model import get_model
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="mkt.clean"
    _version="1.179.0"

    def migrate(self):
        db=get_connection()
        db.execute("delete from mkt_activity")
        db.execute("delete from mkt_target where date is null")
        db.execute("delete from mkt_target_list where date<'2013-01-01'")

Migration.register()
