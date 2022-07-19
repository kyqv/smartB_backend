# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce.model import Model, fields, get_model


class QCResult(Model):
    _name = "qc.result"
    _string = "QC Result"
    _fields = {
        "pick_id": fields.Many2One("stock.picking","Stock Picking",on_delete="cascade",search=True),
        "production_id": fields.Many2One("production.order","Production Order",on_delete="cascade",search=True),
        "move_id": fields.Many2One("stock.move","Stock Move"),
        "date": fields.Date("Date",search=True),
        "product_id": fields.Many2One("product","Product",search=True),
        "lot_id": fields.Many2One("stock.lot","Lot / Serial No.",search=True),
        "total_qty": fields.Decimal("Total Qty"),
        "uom_id": fields.Many2One("uom","UoM"),
        "sample_qty": fields.Decimal("Sample Qty"),
        "test1": fields.Selection([["1","1"],["0","0"]],"Test 1"),
        "test2": fields.Selection([["1","1"],["0","0"]],"Test 2"),
        "test3": fields.Selection([["1","1"],["0","0"]],"Test 3"),
        "test4": fields.Selection([["1","1"],["0","0"]],"Test 4"),
        "test5": fields.Selection([["1","1"],["0","0"]],"Test 5"),
        "test6": fields.Selection([["1","1"],["0","0"]],"Test 6"),
        "test7": fields.Selection([["1","1"],["0","0"]],"Test 7"),
        "test8": fields.Selection([["1","1"],["0","0"]],"Test 8"),
        "result": fields.Selection([["accept","Accept"],["reject","Reject"]],"QC Result",required=True,search=True),
        "inspector_id": fields.Many2One("base.user","Inspector",search=True),
        "reviewer_id": fields.Many2One("base.user","Reviewer",search=True),
        "image": fields.File("Photo"),
    }
    _order = "date,id"

    def default_get(self,field_names=None, context={}, **kw):
        print("QCResult.default_get")
        move_id=context.get("move_id")
        print("move_id",move_id)
        if not move_id:
            return {}
        move=get_model("stock.move").browse(move_id)
        return {
            "pick_id": [move.picking_id.id,move.picking_id.name_get()[0][1]],
            "move_id": [move.id,move.name_get()[0][1]],
            "product_id": [move.product_id.id,move.product_id.name_get()[0][1]], # XXX: simplify this
            "lot_id": [move.lot_id.id,move.lot_id.name_get()[0][1]] if move.lot_id else None,
            "total_qty": move.qty,
            "uom_id": [move.uom_id.id,move.uom_id.name_get()[0][1]],
        }

    def dummy(self,ids,context={}):
        pass

QCResult.register()
