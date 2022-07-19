from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="product.prod_categ"
    _version="1.90.0"

    def migrate(self):
        for obj in get_model("product").search_browse([]):
            if obj.categs:
                continue
            if obj.categ_id:
                obj.write({"categs":[("set",[obj.categ_id.id])]})

Migration.register()
