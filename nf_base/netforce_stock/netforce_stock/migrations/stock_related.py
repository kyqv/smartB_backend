from netforce.model import get_model
from netforce import migration
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="stock.stock_related"
    _version="2.7.0"

    def migrate(self):
        db=get_connection()
        db.execute("UPDATE stock_move SET related_id=(SELECT related_id FROM stock_picking WHERE id=picking_id) WHERE related_id IS NULL")

Migration.register()
