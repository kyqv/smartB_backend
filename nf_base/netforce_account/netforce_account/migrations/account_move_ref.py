from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.move.ref"
    _version="1.130.0"

    def migrate(self):
        for inv in get_model("account.invoice").search_browse([]):
            if not inv.ref:
                continue
            move=inv.move_id
            if not move:
                continue
            if move.ref:
                continue
            move.write({"ref":inv.ref})

Migration.register()
