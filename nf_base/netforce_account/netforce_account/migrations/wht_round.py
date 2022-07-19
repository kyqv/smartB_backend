from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="account.wht_round"
    _version="1.123.0"

    def migrate(self):
        for obj in get_model("account.payment").search_browse([["pay_type","=","invoice"]]):
            if not obj.move_id:
                continue
            for i,line in enumerate(obj.lines):
                amt1=line.amount
                move_line=obj.move_id.lines[1+i]
                amt2=move_line.debit-move_line.credit
                if obj.type=="in":
                    amt2=-amt2
                if abs(amt2-amt1)>0.001:
                    if abs((amt2-amt1)/amt1)>0.05:
                        print("ERROR: not updating, difference too big...")
                        continue
                    print("Updating amount in payment line %s / %s (%s -> %s)"%(obj.number,line.invoice_id.number,amt1,amt2))
                    line.write({"amount":amt2})

Migration.register()
