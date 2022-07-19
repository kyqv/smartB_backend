from netforce.model import get_model
from netforce import migration
from netforce.access import set_active_user, get_active_user, set_active_company, get_active_company

class Migration(migration.Migration):
    _name="hr.multi.company"
    _version="2.12.0"

    def migrate(self):
        company_id=get_active_company()
        user_id=get_active_user()
        set_active_user(1)
        set_active_company(1)
        for dpt in get_model('hr.department').search_browse([]):
            dpt.write({
                'company_id': 1,
            })
        set_active_user(user_id)
        set_active_company(company_id)
    

Migration.register()

