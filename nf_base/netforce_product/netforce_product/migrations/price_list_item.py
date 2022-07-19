from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="product.price_list_item"
    _version="2.10.0"

    def migrate(self):
        for obj in get_model("price.list").search_browse([]):
            remove_ids=[]
            for line in obj.lines:
                for line2 in obj.lines:
                    if line.id==line2.id:
                        continue
                    if line.product_id.id==line2.product_id.id:
                        if line.id < line2.id:
                            remove_ids.append(min(line.id,line2.id))
            get_model("price.list.item").delete(remove_ids)

Migration.register()
