from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="cms.theme"
    _version="1.183.0"

    def migrate(self):
        res=get_model("cms.theme").search([["state","=","active"]])
        if res:
            return
        vals={
            "name": "olsonkart",
        }
        get_model("cms.theme").create(vals) 
        vals={
            "name": "ecom",
        }
        theme_id=get_model("cms.theme").create(vals) 
        obj=get_model("cms.theme").browse([theme_id])
        obj.activate()

Migration.register()
