from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.payment_wht"
    _version="1.103.0"

    def migrate(self):
        for obj in get_model("account.payment").search_browse([]):
            obj.function_store()

Migration.register()
