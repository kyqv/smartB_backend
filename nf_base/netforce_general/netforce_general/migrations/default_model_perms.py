from netforce.model import get_model
from netforce import migration
from netforce import utils
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="general.default_model_perms"
    _version="1.164.0"

    def migrate(self):
        db=get_connection()
        users=db.execute("UPDATE profile SET default_model_perms='full' WHERE default_model_perms IS NULL")

Migration.register()
