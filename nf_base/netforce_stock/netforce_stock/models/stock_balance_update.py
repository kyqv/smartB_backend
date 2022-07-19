from netforce.model import Model, fields, get_model
from datetime import *
import time


class StockBalanceUpdate(Model):
    _name = "stock.balance.update"
    _string = "Stock Balance Update"
    _fields = {
        "product_id": fields.Many2One("product", "Product", required=True, on_delete="cascade"),
        "lot_id": fields.Many2One("stock.lot", "Lot / Serial Number", on_delete="cascade"),
    }

StockBalanceUpdate.register()
