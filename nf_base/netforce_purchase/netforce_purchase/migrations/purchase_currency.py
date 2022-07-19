from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="purchase.purchase_currency"
    _version="1.98.0"

    def migrate(self):
        for obj in get_model("purchase.order.line").search_browse([]):
            obj.function_store()
        for obj in get_model("purchase.order").search_browse([]):
            obj.function_store()

Migration.register()
