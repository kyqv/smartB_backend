from netforce.model import get_model
from netforce import migration
from netforce import utils
from netforce.database import get_connection

class Migration(migration.Migration):
    _name="general.enc_password"
    _version="1.129.0"

    def migrate(self):
        db=get_connection()
        users=db.query("SELECT id,password FROM base_user")
        for user in users:
            if not user.password:
                continue
            if len(user.password)>=20:
                continue
            enc_password=utils.encrypt_password(user.password)
            db.execute("UPDATE base_user SET password=%s WHERE id=%s",enc_password,user.id)

Migration.register()
