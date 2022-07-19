from netforce.model import get_model
from netforce import migration
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="general.share_profile"
    _version="1.88.0"

    def migrate(self):
        db=get_connection()
        res=db.query("SELECT * FROM m2m_share_profile")
        if res:
            print("Share profiles already configured")
            return
        for obj in get_model("share.access").search_browse([]):
            if obj.profile_id:
                vals={
                    "select_profile": "include",
                    "profiles": [("set",[obj.profile_id.id])],
                }
            else:
                vals={
                    "select_profile": "all",
                }
            obj.write(vals)

Migration.register()
