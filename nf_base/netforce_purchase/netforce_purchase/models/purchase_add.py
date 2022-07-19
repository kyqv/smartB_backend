from netforce.model import Model, fields, get_model


class PurchaseAdd(Model):
    _name = "purchase.add"
    _fields = {
        "purchase_id": fields.Many2One("purchase.order", "Purchase Order", required=True),
        "master_product_id": fields.Many2One("product","Master Product",condition=[["type","=","master"]]),
    }

    def add_products(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.purchase_id:
            raise Exception("Purchase order not selected")
        master=obj.master_product_id
        if not master:
            raise Exception("Missing master product")
        n=0
        for prod in master.variants:
            vals={
                "order_id": obj.purchase_id.id,
                "product_id": prod.id,
                "description": prod.description or prod.name,
                "qty": 1,
                "unit_price": prod.purchase_price or 0,
                "uom_id": prod.uom_id.id,
                "tax_id": prod.purchase_tax_id.id,
            }
            get_model("purchase.order.line").create(vals)
            n+=1
        return {
            "alert": "%d products added"%n,
        }

PurchaseAdd.register()
