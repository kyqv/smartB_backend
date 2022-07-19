from netforce.model import get_model
from netforce import migration
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="stock.stock_journal"
    _version="1.115.0"

    def migrate(self):
        res=get_model("stock.journal").search([])
        if res:
            print("Stock journals already created")
            return
        vals={
            "name": "Goods Receipts",
            "type": "in",
        }
        in_id=get_model("stock.journal").create(vals)
        vals={
            "name": "Goods Transfers",
            "type": "internal",
        }
        internal_id=get_model("stock.journal").create(vals)
        vals={
            "name": "Goods Issues",
            "type": "out",
        }
        out_id=get_model("stock.journal").create(vals)
        db=get_connection()
        db.execute("UPDATE stock_picking SET journal_id=%s WHERE type='in'",in_id)
        db.execute("UPDATE stock_picking SET journal_id=%s WHERE type='internal'",internal_id)
        db.execute("UPDATE stock_picking SET journal_id=%s WHERE type='out'",out_id)

Migration.register()
