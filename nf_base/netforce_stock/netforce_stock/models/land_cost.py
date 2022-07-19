from netforce.model import Model, fields, get_model
import time
from netforce.utils import get_data_path

class LandCost(Model):
    _name = "land.cost"
    _name_field = "number"
    _string = "Land Costs"
    _fields = {
        "number": fields.Char("Number",required=True,search=True),
        "date": fields.Date("Date",required=True,search=True),
        "state": fields.Selection([["draft","Draft"],["posted","Posted"]],"Status",search=True,required=True),
        "invoices": fields.One2Many("account.invoice","land_cost_id","Invoices"),
        "amount": fields.Decimal("Total Cost Amount"),
        "alloc_amount": fields.Decimal("Allocated Cost Amount",function="get_alloc_amount"),
    }

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence("landed_cost")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id)
            res = self.search([["number", "=", num]])
            if not res:
                return num
            get_model("sequence").increment_number(seq_id)

    _defaults={
        "state": "draft",
        "number": _get_number,
        "date": lambda *a: time.strftime("%Y-%m-%d"),
    }

    def alloc_cost(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.amount:
            raise Exception("Missing cost amount")
        total=0
        for inv in obj.invoices:
            for line in inv.lines:
                total+=line.amount
        if not total:
            return
        for inv in obj.invoices:
            for line in inv.lines:
                cost=obj.amount*(line.amount or 0)/total
                line.write({"land_cost_amount":cost})

    def get_alloc_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            for inv in obj.invoices:
                for line in inv.lines:
                    amt+=line.land_cost_amount or 0
            vals[obj.id]=amt
        return vals

LandCost.register()
