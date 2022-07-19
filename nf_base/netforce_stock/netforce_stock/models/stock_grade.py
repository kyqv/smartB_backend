from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path
import time


class Grade(Model):
    _name = "stock.grade"
    _string = "Product Grading"
    _name_field = "number"
    _fields = {
        "date": fields.DateTime("Date", required=True, search=True),
        "number": fields.Char("Number", required=True, search=True),
        "ref": fields.Char("Ref",search=True),
        "related_id": fields.Reference([["purchase.order","Order"],["stock.picking","Picking"],["production.order","Production Order"]],"Related To"),
        "location_id": fields.Many2One("stock.location", "Grading Location", condition=[["type", "=", "internal"]], search=True, required=True),
        "location_ga_id": fields.Many2One("stock.location", "Grade-A Location", condition=[["type", "=", "internal"]], search=True),
        "location_gb_id": fields.Many2One("stock.location", "Grade-B Location", search=True),
        "location_waste_id": fields.Many2One("stock.location", "Waste Location", search=True),
        "notes": fields.Text("Notes"),
        "state": fields.Selection([["draft", "Draft"], ["done", "Completed"], ["voided", "Voided"]], "Status", required=True, search=True),
        "lines": fields.One2Many("stock.grade.line","grade_id","Lines"),
        "stock_moves": fields.One2Many("stock.move", "related_id", "Stock Movements"),
        "product_id": fields.Many2One("product","Graded Product",search=True,condition=[["type","=","stock"]],required=True),
        "qty": fields.Decimal("Graded Qty",required=True),
        "qty_ga": fields.Decimal("Grade-A Qty"),
        "qty_waste": fields.Decimal("Waste Qty"),
        "qty_loss": fields.Decimal("Loss Qty",function="get_qty_loss"),
        "purchase_id": fields.Many2One("purchase.order","Purchase Order"),
        "production_id": fields.Many2One("production.order","Production Order"),
        "qty_remain": fields.Decimal("Remaining Qty",function="get_qty_remain"),
    }
    _order = "date desc,id desc"

    def _get_number(self, context={}):
        seq_id = None
        seq_id = get_model("sequence").find_sequence("stock_grade")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id)

    _defaults = {
        "state": "draft",
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "number": _get_number,
    }

    def validate(self, ids, context={}):
        obj = self.browse(ids)[0]
        settings = get_model("settings").browse(1)
        res = get_model("stock.location").search([["type", "=", "transform"]])
        if not res:
            raise Exception("Missing transform location")
        trans_loc_id = res[0]
        res = get_model("stock.location").search([["type", "=", "inventory"]])
        if not res:
            raise Exception("Missing inventory loss location")
        loss_loc_id = res[0]
        journal_id=settings.transform_journal_id.id
        if not journal_id:
            raise Exception("Missing transform journal")
        move_ids=[]
        vals = {
            "date": obj.date,
            "journal_id": journal_id,
            "product_id": obj.product_id.id,
            "qty": obj.qty,
            "uom_id": obj.product_id.uom_id.id,
            "related_id": "stock.grade,%s"%obj.id,
            "location_from_id": obj.location_id.id,
            "location_to_id": trans_loc_id,
        }
        move_id = get_model("stock.move").create(vals)
        move_ids.append(move_id)
        for line in obj.lines:
            vals = {
                "date": obj.date,
                "journal_id": journal_id,
                "product_id": line.product_id.id,
                "qty": line.qty,
                "uom_id": line.product_id.uom_id.id,
                "related_id": "stock.grade,%s"%obj.id,
                "location_from_id": trans_loc_id,
                "location_to_id": line.location_id.id,
                "cost_price": line.unit_price,
                "cost_amount": line.amount,
            }
            move_id = get_model("stock.move").create(vals)
            move_ids.append(move_id)
        get_model("stock.move").set_done(move_ids)
        obj.write({"state": "done"})

    def void(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.stock_moves.delete()
        obj.write({"state": "voided"})

    def to_draft(self, ids, context={}):
        obj = self.browse(ids)[0]
        obj.stock_moves.delete()
        obj.write({"state": "draft"})

    def onchange_product(self, context={}):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        prod_id = line.get("product_id")
        prod = get_model("product").browse(prod_id)
        line["uom_id"] = prod.uom_id.id
        line["qty"]=1
        return data

    def delete(self,ids,context={}):
        for obj in self.browse(ids):
            if obj.state=="done":
                raise Exception("Can not delete product transforms in this status")
        super().delete(ids,context=context)

    def get_qty_loss(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            qty=obj.qty or 0
            for line in obj.lines:
                qty-=line.qty or 0
            vals[obj.id]=qty
        return vals

    def update_amount(self, context={}):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        qty=line.get("qty")
        unit_price=line.get("unit_price")
        amount=line.get("amount")
        if qty is not None and unit_price is not None:
            line["amount"]=qty*unit_price
        elif qty and amount is not None:
            line["unit_price"]=amount/qty
        return data

    def onchange_amount(self, context={}):
        data = context["data"]
        path = context["path"]
        line = get_data_path(data, path, parent=True)
        qty=line.get("qty")
        amount=line.get("amount")
        if qty and amount is not None:
            line["unit_price"]=amount/qty
        data=self.update_amount(context=context)
        return data

Grade.register()
