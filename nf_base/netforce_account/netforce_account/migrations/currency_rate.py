from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.currency_rate"
    _version="1.128.0"

    def migrate(self):
        for rate in get_model("currency.rate").search_browse([]):
            if not rate.buy_rate and not rate.sell_rate:
                rate.write({
                    "buy_rate": rate.rate,
                    "sell_rate": rate.rate,
                })

Migration.register()
