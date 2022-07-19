from netforce.model import Model, fields, get_model
import time
import os
from netforce import ipc
from netforce import database

class UomConv(Model):
    _name = "uom.conv"
    _string = "UoM Conversion Factor"
    _fields = {
        "uom_from_id": fields.Many2One("uom","From UoM",required=True),
        "uom_to_id": fields.Many2One("uom","To UoM",required=True),
        "factor": fields.Decimal("Conversion Factor",required=True,scale=6),
        "product_id": fields.Many2One("product","Product",search=True),
        "product_categ_id": fields.Many2One("product.categ","Product Category",search=True),
    }

    def get_factor(self,uom_from_id,uom_to_id,product_id=None):
        conv_id=None
        uom_cond=["or",[["uom_from_id","=",uom_from_id],["uom_to_id","=",uom_to_id]],[["uom_from_id","=",uom_to_id],["uom_to_id","=",uom_from_id]]]
        if product_id:
            cond=[uom_cond,["product_id","=",product_id]]
        res=get_model("uom.conv").search(cond)
        if res:
            conv_id=res[0]
        if not conv_id and product_id:
            prod=get_model("product").browse(product_id)
            if prod.categ_id:
                cond=[uom_cond,["product_categ_id","=",prod.categ_id.id]]
                res=get_model("uom.conv").search(cond)
                if res:
                    conv_id=res[0]
        if not conv_id:
            return None
        conv=self.browse(conv_id)
        if conv.uom_from_id.id==uom_from_id and conv.uom_to_id.id==uom_to_id:
            return conv.factor
        elif conv.uom_from_id.id==uom_to_id and conv.uom_to_id.id==uom_from_id:
            return 1/conv.factor if conv.factor else None

UomConv.register()
