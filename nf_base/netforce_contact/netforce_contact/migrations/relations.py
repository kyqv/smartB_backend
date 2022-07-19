from netforce.model import get_model
from netforce import migration

class Migration(migration.Migration):
    _name="contact.relations"
    _version="1.88.0"

    def migrate(self):
        res=get_model("partner.relation.type").search_browse([])
        if res:
            print("Contact relations already created")
            return
        vals={
            "name": "Sub-contact",
        }
        type_id=get_model("partner.relation.type").create(vals)
        for obj in get_model("partner").search_browse([]):
            if obj.partner_id:
                vals={
                    "from_partner_id": obj.id,
                    "to_partner_id": obj.partner_id.id,
                    "rel_type_id": type_id,
                }
                get_model("partner.relation").create(vals)

Migration.register()
