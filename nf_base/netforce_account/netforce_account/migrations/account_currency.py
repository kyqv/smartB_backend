from netforce.model import get_model
from netforce import migration
from netforce import access

class Migration(migration.Migration):
    _name="account.account_currency"
    _version="2.10.0"

    def migrate(self):
        comp_ids=get_model("company").search([])
        for comp_id in comp_ids:
            access.set_active_company(comp_id)
            settings=get_model("settings").browse(1)
            currency_id=settings.currency_id.id
            if not currency_id:
                print("WARNING: no currency for company %d"%comp_id)
                continue
            print("company %d -> currency %d"%(comp_id,currency_id))
            acc_ids=get_model("account.account").search([["company_id","=",comp_id]])
            get_model("account.account").write(acc_ids,{"currency_id":currency_id})

Migration.register()
