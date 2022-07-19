from netforce.model import Model, fields, get_model
from netforce import access
import time


class Settings(Model):
    _name = "shopee.settings"
    _fields = {
        "default_uom_id": fields.Many2One("uom","Default UoM"),
        "order_auto_copy_to_sale": fields.Boolean("Auto Copy Shopee Order to Sale Order when Syncing"),
        "order_auto_copy_to_picking": fields.Boolean("Auto Copy Shopee Order to Goods Issue when Syncing"),
        "order_auto_complete_picking": fields.Boolean("Auto Complete Goods Issue when Syncing"),
        "use_order_num_for_picking": fields.Boolean("Use Order Number for Goods Issue"),
        "auto_refresh_tokens": fields.Boolean("Auto Refresh Token"),
        "enable_webhook": fields.Boolean("Enable Webhook"),
        "check_stock": fields.Boolean("Check Stock"),
    }
    
    def read(self, ids, field_names=None, load_m2o=True, load_all_trans=False, get_time=False, context={}):
        res = self.search([["id","in",ids]])
        print("res",res)
        if len(res) == 0:
            print("creating new settings")
            defaults = self.default_get()
            new_id = self.create(defaults)
            print("new_id", new_id)
        return super().read(ids, field_names=field_names, load_m2o=load_m2o, load_all_trans=load_all_trans, get_time=get_time, context=context) 

Settings.register()
