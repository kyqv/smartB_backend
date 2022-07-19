from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.statement_bals"
    _version="1.128.0"

    def migrate(self):
        for st in get_model("account.statement").search_browse([]):
            if not st.lines:
                continue
            first=st.lines[0]
            last=st.lines[-1]
            st.write({
                "date_start": first.date,
                "balance_start": first.balance-(first.received or 0)+(first.spent or 0),
                "date_end": last.date,
                "balance_end": last.balance,
            })

Migration.register()
