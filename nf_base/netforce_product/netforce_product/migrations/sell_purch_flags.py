from netforce.model import get_model
from netforce import migration
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="product.sell_purch_flags"
    _version="1.137.0"

    def migrate(self):
        db=get_connection()
        db.execute("UPDATE product SET can_sell=true WHERE can_sell IS NULL")
        db.execute("UPDATE product SET can_purchase=true WHERE can_purchase IS NULL")

Migration.register()
