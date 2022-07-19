from netforce.model import Model, fields, get_model
from netforce import access
from netforce import config
from netforce import utils
from datetime import *
import time
import requests
import hashlib
import hmac


class Picking(Model):
    _inherit = "stock.picking"
    _fields = {
        #"sync_records": fields.One2Many("sync.record","related_id","Sync Records"),
        "recipient_first_name": fields.Char("First Name"),
        "recipient_last_name": fields.Char("Last Name"),
        "recipient_phone": fields.Char("Phone"),
        "recipient_address": fields.Char("Address"),
        "recipient_address2": fields.Char("Address2"),
        "recipient_postcode": fields.Char("Postcode"),
        "recipient_city": fields.Char("City"),
        "recipient_province": fields.Char("Province"),
        "recipient_country": fields.Char("Country"),
    }
    
    """
    def get_shopee_order(self,acc_id,order,context={}):
        acc = get_model("shopee.account").browse(acc_id)
        if not acc.stock_journal_id:
            raise Exception("Missing Stock Journal for Shopee Account: %s" % acc.name)
        if not acc.stock_journal_id.location_from_id:
            raise Exception("Missing From Location in Stock Journal: %s" % acc.stock_journal_id.name)
        if not acc.stock_journal_id.location_to_id:
            raise Exception("Missing To Location in Stock Journal: %s" % acc.stock_journal_id.name)
        pick_vals={
            "number": "Shopee - %s" % order["order_sn"],
            "type": "out",
            "contact_id": context.get("cont_id"),
            "related_id": "sale.order,%s" % context.get("sale_id") if context.get("sale_id") else None,
            "journal_id": acc.stock_journal_id.id,
            "date": datetime.fromtimestamp(order["create_time"]).strftime("%Y-%m-%d"),
            "recipient_first_name": order["recipient_address"]["name"],
            "recipient_address": order["recipient_address"]["full_address"],
            "recipient_phone": order["recipient_address"]["phone"],
            "recipient_postcode": order["recipient_address"]["zipcode"],
            "recipient_city": order["recipient_address"]["city"],
            "recipient_province": order["recipient_address"]["state"],
            "recipient_country": order["recipient_address"]["region"],
            "lines": [],
            "sync_records": [("create",{
                "sync_id": order["order_sn"],
                "account_id": "shopee.account,%s"%acc.id,
            })],
        }
        for it in order["item_list"]:
            res=get_model("sync.record").search([["sync_id","=",str(it["item_id"])],["related_id","like","product"],["account_id","=","shopee.account,%s"%acc_id]])
            if not res:
                raise Exception("Product not found: %s"%it["item_id"])
            sync_id= res[0]
            sync=get_model("sync.record").browse(sync_id)
            prod=sync.related_id
            line_vals={
                "product_id": prod.id,
                "description": it["item_name"],
                "qty": it["model_quantity_purchased"],
                "uom_id": prod.uom_id.id,
                "location_from_id": acc.stock_journal_id.location_from_id.id,
                "location_to_id": acc.stock_journal_id.location_to_id.id,
                
            }
            pick_vals["lines"].append(("create",line_vals))
        pick_sync = get_model("sync.record").search_browse([
            ["account_id","=","shopee.account,%s"%acc_id],
            ["related_id","like","stock.picking"],
            ["sync_id","=",str(order["order_sn"])]
        ]) 
        picks = get_model("stock.picking").search_browse([["number","=","Shopee - %s" % order["order_sn"]]])
        pick = None
        if pick_sync:
            pick = pick_sync[0].related_id.id if pick_sync[0].related_id else None
        elif picks:
            pick = picks[0]
        if pick:
            delete_lines = [l.id for l in pick.lines]
            if delete_lines:
                pick_vals["lines"].append(["delete",delete_lines])
            pick.write(pick_vals)
        else:
            print("creating Stock Picking: %s"%pick_vals)
            pick_id = get_model("stock.picking").create(pick_vals)
            pick = get_model("stock.picking").browse(pick_id)
        pick.set_done_fast()
        return pick_id
    """

Picking.register()
