from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="sale.sale_currency"
    _version="1.97.0"

    def migrate(self):
        for obj in get_model("sale.order.line").search_browse([]):
            obj.function_store()
        for obj in get_model("sale.order").search_browse([]):
            obj.function_store()

Migration.register()
