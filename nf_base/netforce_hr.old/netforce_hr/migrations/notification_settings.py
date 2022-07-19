from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="notification.settings"
    _version="1.179.0"

    def migrate(self):
        res=get_model("hr.notification").search([])
        if res:
            return
        vals={
            'subject': "Happy Birth Day",
            'description': "I wish you always be healthy happy in your life and achieve all your goal."
        }
        obj_id=get_model("hr.notification").create(vals)
        print("hr.notification ", obj_id)

Migration.register()

