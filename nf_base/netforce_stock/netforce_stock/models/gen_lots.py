from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path
import time


class GenLots(Model):
    _name = "gen.lots"
    _string = "Gen Lots"
    _transient=True
    _fields = {
        "product_id": fields.Many2One("product", "Product", required=True),
        "sequence_id": fields.Many2One("sequence", "Batch Sequence", condition=[["type","=","stock_lot"]],required=True),
        "prefix": fields.Char("Batch Prefix",required=True),
        "num_lots": fields.Integer("Number Of Lots", required=True),
        "padding": fields.Integer("Lot Number Padding", required=True),
    }
    _defaults={
        "padding": 3,
    }

    def gen_lots(self,ids,context={}):
        print("gen_lots")
        obj=self.browse(ids[0])
        seq_id=obj.sequence_id.id
        prefix=obj.prefix
        for i in range(0,obj.num_lots):
            num = "%s%.*d" % (prefix, obj.padding,i+1)
            vals={
                "number": num,
                "product_id": obj.product_id.id,
                "received_date": time.strftime("%Y-%m-%d"),
            }
            get_model("stock.lot").create(vals)
        prod=obj.product_id
        ctx={
            "categ_code": prod.categ_id.code if prod.categ_id else None,
            "parent_categ_code": prod.categ_id.parent_id.code if prod.categ_id and prod.categ_id.parent_id else None,
        }
        print("ctx",ctx)
        get_model("sequence").increment_number(seq_id,context=ctx)
        return {
            "next": {
                "name": "stock_lot",
            },
            "alert": "%s lots created"%(obj.num_lots,),
        }

    def onchange_sequence(self,context={}):
        data=context["data"]
        prod_id=data["product_id"]
        prod=get_model("product").browse(prod_id)
        sequence_id=data["sequence_id"]
        seq=get_model("sequence").browse(sequence_id)
        ctx={
            "categ_code": prod.categ_id.code if prod.categ_id else None,
            "parent_categ_code": prod.categ_id.parent_id.code if prod.categ_id and prod.categ_id.parent_id else None,
        }
        prefix=get_model("sequence").get_next_number(seq.id,context=ctx)
        data["prefix"]=prefix
        return data

GenLots.register()
