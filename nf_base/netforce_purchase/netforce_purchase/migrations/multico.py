from netforce import migration
from netforce.model import get_model
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="purchase.multico"
    _version="1.155.0"

    def migrate(self):
        db=get_connection()
        db.execute("update purchase_order set company_id=1 where company_id is null")

Migration.register()
