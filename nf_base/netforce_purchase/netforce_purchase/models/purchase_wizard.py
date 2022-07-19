from netforce.model import Model, fields, get_model


class PurchaseWizard(Model):
    _name = "purchase.wizard"
    _fields = {
        "product_id": fields.Many2One("product", "Product", required=True),
        "product_supplier_id": fields.Many2One("product.supplier", "Supplier", required=True),
    }

    def make_po(self,ids,context={}):
        obj=self.browse(ids[0])
        vals={
            "contact_id": obj.product_supplier_id.supplier_id.id,
        }
        line_vals={
            "product_id": obj.product_id.id,
            "description": obj.product_id.name,
            "unit_price": obj.product_supplier_id.purchase_price,
            "qty": 1,
            "uom_id": obj.product_id.uom_id.id,
            "tax_id": obj.product_id.purchase_tax_id.id,
        }
        vals["lines"]=[("create",line_vals)]
        purch_id=get_model("purchase.order").create(vals)
        purch=get_model("purchase.order").browse(purch_id)
        return {
            "next": {
                "name": "purchase",
                "mode": "form",
                "active_id": purch_id,
            },
            "alert": "Purchase order %s created successfully."%purch.number,
        }

PurchaseWizard.register()
