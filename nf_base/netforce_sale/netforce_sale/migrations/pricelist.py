from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="sale.pricelist"
    _version="1.98.0"

    def migrate(self):
        for obj in get_model("price.list").search_browse([]):
            if not obj.type:
                obj.write({"type":"sale"})

Migration.register()
