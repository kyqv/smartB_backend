from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.tracking"
    _version="1.94.0"

    def migrate(self):
        for obj in get_model("account.track.categ").search_browse([]):
            if not obj.type:
                obj.write({"type":"1"})

Migration.register()
