from netforce import migration
from netforce.model import get_model
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="account.multico"
    _version="1.111.0"

    def migrate(self):
        db=get_connection()
        print("accounts...")
        db.execute("update account_account set company_id=1 where company_id is null")
        print("journal entries...")
        db.execute("update account_move set company_id=1 where company_id is null")
        print("invoices...")
        db.execute("update account_invoice set company_id=1 where company_id is null")
        print("payments...")
        db.execute("update account_payment set company_id=1 where company_id is null")
        print("transfers...")
        db.execute("update account_transfer set company_id=1 where company_id is null")
        print("statements...")
        db.execute("update account_statement set company_id=1 where company_id is null")

Migration.register()
