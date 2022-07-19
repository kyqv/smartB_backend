from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path
import time


class GradeLine(Model):
    _name = "stock.grade.line"
    _fields = {
        "grade_id": fields.Many2One("stock.grade","Grading",required=True,on_delete="cascade"),
        "product_id": fields.Many2One("product","Product",search=True,condition=[["type","=","stock"]],required=True),
        "qty": fields.Decimal("Qty",required=True),
        "lot_id": fields.Many2One("stock.lot","Lot",search=True),
        "product_gb_id": fields.Many2One("product","Grade-B Product",search=True,condition=[["type","=","stock"]]),
        "qty_ga": fields.Decimal("Grade-A Qty"),
        "qty_gb": fields.Decimal("Grade-B Qty"),
        "qty_waste": fields.Decimal("Waste Qty"),
        "qty_loss": fields.Decimal("Loss Qty",function="get_qty_loss"),
        "uom_id": fields.Many2One("uom","UoM"),
        "related_id": fields.Reference([["stock.picking","Picking"],["production.order","Production Order"]],"Related To"),
        "picking_id": fields.Many2One("stock.picking","Picking"),
        "purchase_id": fields.Many2One("purchase.order","Purchase Order"),
        "production_id": fields.Many2One("production.order","Production Order"),
        "qty_remain": fields.Decimal("Remaining Qty",function="get_qty_remain"),
        "location_id": fields.Many2One("stock.location", "Location", condition=[["type", "=", "internal"]], search=True, required=True),
        "unit_price": fields.Decimal("Unit Price"),
        "amount": fields.Decimal("Amount"),
    }

    def get_qty_loss(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            qty_loss=obj.qty-(obj.qty_ga or 0)-(obj.qty_gb or 0)-(obj.qty_waste or 0)
            vals[obj.id]=qty_loss
        return vals

    def get_qty_remain(self,ids,context={}):
        print("get_qty_remain",ids)
        purch_ids=[]
        for obj in self.browse(ids):
            if obj.purchase_id:
                purch_ids.append(obj.purchase_id.id)
        purch_ids=list(set(purch_ids))
        grade_ids=[]
        qtys_purch={}
        print("purch_ids",purch_ids)
        for purch in get_model("purchase.order").browse(purch_ids):
            for line in purch.lines:
                k=(purch.id,line.product_id.id)
                qtys_purch.setdefault(k,0)
                qtys_purch[k]+=line.qty_received
            for line in purch.gradings:
                grade_ids.append(line.grade_id.id)
        print("qtys_purch",qtys_purch)
        grade_ids=list(set(grade_ids))
        print("grade_ids",grade_ids)
        qtys_grade={}
        for grade in get_model("stock.grade").browse(grade_ids):
            for line in grade.lines:
                if line.purchase_id:
                    k=(line.purchase_id.id,line.product_id.id)
                    qtys_grade.setdefault(k,0)
                    qtys_grade[k]+=line.qty
        print("qtys_grade",qtys_grade)
        vals={}
        for obj in self.browse(ids):
            k=(obj.purchase_id.id,obj.product_id.id)
            qty_purch=qtys_purch.get(k,0)
            qty_grade=qtys_grade.get(k,0)
            qty_remain=qty_purch-qty_grade
            vals[obj.id]=qty_remain
        return vals

    def get_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=(obj.qty or 0)*(obj.unit_price or 0)
        return vals

GradeLine.register()
