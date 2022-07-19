from netforce.model import Model, fields, get_model
from netforce import access
from datetime import *


class SaleOrder(Model):
    _inherit = "sale.order"
    _fields = {
        "sync_records": fields.One2Many("sync.record","related_id","Sync Records"),
    }

    """
    def get_shopee_order(self,acc_id,order,context={}):
        if not acc_id: 
            raise Exception("Missing Shopee acc_id")
        acc = get_model("shopee.account").browse(acc_id)
        if not acc:
            raise Exception("Shopee Account not Found for ID: %s" % acc_id)
        if not order:
            raise Exception("Missing Order Details")
        cont_id = context.get("cont_id")
        if not cont_id:
            raise Exception("Unable to Create Sales Order without Contact. Please enable contact module in Shopee Settings")
        sale_vals={
            "contact_id": cont_id,
            "date": datetime.fromtimestamp(order["create_time"]).strftime("%Y-%m-%d"),
            "due_date": datetime.fromtimestamp(order["ship_by_date"]).strftime("%Y-%m-%d"),
            "other_info": order["note"],
            "lines": [],
            "sync_records": [("create",{
                "sync_id": order["order_sn"],
                "account_id": "shopee.account,%s"%acc_id,
            })],
        }
        for it in order["item_list"]:
            #res=get_model("product").search([["sync_records.shopee_id","=",it["item_id"]]])
            res=get_model("sync.record").search([["sync_id","=",str(it["item_id"])],["related_id","like","product"],["account_id","=","shopee.account,%s"%acc_id]]) # XXX
            if not res:
                raise Exception("Product not found: %s"%it["item_id"])
            sync_id=res[0]
            sync=get_model("sync.record").browse(sync_id)
            prod_id=sync.related_id.id
            line_vals={
                "product_id": prod_id,
                "description": it["item_name"],
                "qty": it["model_quantity_purchased"],
                "unit_price": it["model_discounted_price"],
            }
            sale_vals["lines"].append(("create",line_vals))
        sale_id = get_model("sale.order").create(sale_vals)
        return sale_id
        """

SaleOrder.register()
