from netforce.model import Model, fields, get_model
from netforce import access


class Contact(Model):
    _inherit = "contact"
    _fields = {
        "sync_records": fields.One2Many("sync.record","related_id","Sync Records"),
        "sync_id": fields.Char("Sync ID",function="get_sync_id",function_search="search_sync_id"),
    }
    def get_sync_id(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            sync_id=None
            for sync in obj.sync_records:
                sync_id=sync.sync_id
                break
            vals[obj.id]=sync_id
            return vals

    def search_sync_id(self, clause, context={}):
        sync_id = clause[2]
        records = get_model("sync.record").search_browse([["related_id","like","contact"],["sync_id","=",sync_id]])
        contact_ids = [r.related_id.id  for r in records if r.related_id]
        cond = [["id","in",contact_ids]]
        return cond

    def get_shopee_contact(self, acc_id, order, context={}):
        if not acc_id:
            raise Exception("Missing Shopee acc_id")
        acc = get_model("shopee.account").browse(acc_id)
        if not acc:
            raise Exception("Shopee Account not found with ID %s" % acc_id)
        if not order:
            raise Exception("Missing Order Details")
        cont_vals={
            "type": "person",
            "last_name": order["buyer_username"] or "N/A",
            "sync_records": [("create",{
                "sync_id": order["buyer_user_id"],
                "account_id": "shopee.account,%s"%acc.id,
            })],
        }
        addr_vals={
            "address": order["recipient_address"]["full_address"] or "N/A",
            "postal_code": order["recipient_address"]["zipcode"],
            "city": order["recipient_address"]["city"],
            "phone": order["recipient_address"]["phone"],
        }
        contact_sr_ids = get_model("sync.record").search_browse([["related_id","like","contact"],["sync_id","=",str(order["buyer_user_id"])],["account_id","=","shopee.account,%s"%acc_id]])

        if len(contact_sr_ids) > 0:
            cont_id = contact_sr_ids[0].related_id.id
            get_model("contact").write([cont_id],cont_vals)
            conds = [["contact_id","=",cont_id]]
            for f in addr_vals:
                conds.append([f,"=",addr_vals[f]])
            addresses = get_model("address").search(conds)
            if len(addresses) > 0:
                address_id = addresses[0]
            else:
                addr_vals["contact_id"] = cont_id
                address_id = get_model("address").create(addr_vals)
        else:
            cont_id=get_model("contact").create(cont_vals)
            context["cont_id"] = cont_id
            addr_vals["contact_id"] = cont_id
            address_id = get_model("address").create(addr_vals)
        return cont_id
        
Contact.register()
