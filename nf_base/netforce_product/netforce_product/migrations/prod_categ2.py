from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="product.prod_categ2"
    _version="2.10.0"

    def migrate(self):
        for obj in get_model("product").search_browse([]):
            if not obj.categ_id and obj.categs:
                obj.write({"categ_id":obj.categs[0].id})

Migration.register()
