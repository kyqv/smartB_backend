from netforce.model import get_model
from netforce import migration
from netforce import database

class Migration(migration.Migration):
    _name="account.credit_remain_cur"
    _version="2.5.0"

    def migrate(self):
        db=database.get_connection()
        db.execute("UPDATE account_invoice SET amount_credit_remain_cur=amount_credit_remain WHERE amount_credit_remain_cur IS NULL AND amount_credit_remain IS NOT NULL")

Migration.register()
