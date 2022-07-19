from netforce.model import Model, fields, get_model


class Merge(Model):
    _name = "merge.contact"
    _fields = {
        "from_contact_id": fields.Many2One("contact", "Delete Contact", required=True),
        "to_contact_id": fields.Many2One("contact", "Merge With Contact", required=True),
    }

    def merge(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.to_contact_id.id==obj.from_contact_id.id:
            raise Exception("Contacts are the same")
        fields=["email","phone","tax_no"]
        for n in fields:
            val=obj.from_contact_id[n]
            if val and not obj.to_contact_id[n]:
                obj.to_contact_id.write({n:val})
        desc="Merged with %s (%s)"%(obj.to_contact_id.name,obj.to_contact_id.code)
        obj.from_contact_id.write({"state":"inactive","description":desc,"active":False})
        for r in get_model("account.invoice").search_browse([["contact_id","=",obj.from_contact_id.id]]):
            r.write({"contact_id":obj.to_contact_id.id})
        for r in get_model("account.payment").search_browse([["contact_id","=",obj.from_contact_id.id]]):
            r.write({"contact_id":obj.to_contact_id.id})
        for r in get_model("account.move.line").search_browse([["contact_id","=",obj.from_contact_id.id]]):
            r.write({"contact_id":obj.to_contact_id.id})
        for r in get_model("stock.picking").search_browse([["contact_id","=",obj.from_contact_id.id]]):
            r.write({"contact_id":obj.to_contact_id.id})
        for r in get_model("stock.move").search_browse([["contact_id","=",obj.from_contact_id.id]]):
            r.write({"contact_id":obj.to_contact_id.id})
        for r in get_model("sale.order").search_browse([["contact_id","=",obj.from_contact_id.id]]):
            r.write({"contact_id":obj.to_contact_id.id})
        for r in get_model("purchase.order").search_browse([["contact_id","=",obj.from_contact_id.id]]):
            r.write({"contact_id":obj.to_contact_id.id})
        for r in get_model("jc.job").search_browse([["contact_id","=",obj.from_contact_id.id]]):
            r.write({"contact_id":obj.to_contact_id.id})
        return {
            "alert": "Contacts merged successfully",
        }

Merge.register()
