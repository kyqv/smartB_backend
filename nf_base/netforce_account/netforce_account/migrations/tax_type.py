from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.tax_type"
    _version="1.103.0"

    def migrate(self):
        for obj in get_model("account.tax.component").search_browse([]):
            if obj.type=="tax_inv":
                obj.write({"type":"vat"})
            elif obj.type=="tax_pay":
                obj.write({"type":"vat_defer"})

Migration.register()
