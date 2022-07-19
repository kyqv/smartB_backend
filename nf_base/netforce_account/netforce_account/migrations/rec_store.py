from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.rec_store"
    _version="1.83.0"

    def migrate(self):
        for obj in get_model("account.reconcile").search_browse([]):
            obj.function_store()

Migration.register()
