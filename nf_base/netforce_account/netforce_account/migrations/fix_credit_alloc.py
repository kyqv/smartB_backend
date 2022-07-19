from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.fix_credit_alloc"
    _version="1.137.0"

    def migrate(self):
        for alloc in get_model("account.credit.alloc").search_browse([["credit_id.inv_type","=","credit"],["move_id","!=",None]]):
            print("Deleting duplicate journal entry for credit note %s"%alloc.credit_id.number)
            alloc.move_id.void()
            alloc.move_id.delete()

Migration.register()
