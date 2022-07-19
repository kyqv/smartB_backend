from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.move_state"
    _version="1.81.0"

    def migrate(self):
        for line in get_model("account.move.line").search_browse([]):
            line.write({"move_state":line.move_id.state})

Migration.register()
