from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.tax_date"
    _version="1.184.0"

    def migrate(self):
        for obj in get_model("account.move.line").search_browse([["tax_comp_id","!=",None],["tax_date","=",None]]):
            obj.write({"tax_date":obj.move_id.date})

Migration.register()
