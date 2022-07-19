from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path
import time


class Transfer(Model):
    _name = "stock.transfer"
    _string = "Transfer Stock"
    _transient=True
    _fields = {
        "journal_id": fields.Many2One("stock.journal", "Journal", required=True),
        "lot_no": fields.Char("Lot / Serial Number"),
    }

    def validate(self,ids,context={}):
        obj=self.browse(ids[0])
        journal=obj.journal_id
        if not journal:
            raise Exception("Missing journal")
        if not obj.lot_no:
            raise Exception("Missing lot number")
        res=get_model("stock.lot").search([["number","=",obj.lot_no]])
        if not res:
            raise Exception("Lot number not found: %s"%obj.lot_no)
        lot_id=res[0]
        lot=get_model("stock.lot").browse(lot_id)
        prod=lot.product_id
        if not prod:
            raise Exception("Missing product in lot")
        res=get_model("stock.move").validate_transaction(journal_code=journal.code,product_id=prod.id,qty=1,lot_id=lot.id)
        pick_no=res["number"]
        return {
            "next": {
                "name": "stock_transfer_m",
            },
            "alert": "Transfer success: %s"%pick_no,
        }

Transfer.register()
