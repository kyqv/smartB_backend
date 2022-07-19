from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path
from datetime import *
from dateutil.relativedelta import *
import time


class GenReport(Model):
    _name = "gen.sale.report"
    _transient = True
    _fields = {
        "date_from": fields.Date("From Date",required=True),
    }
    _defaults={
        "date_from": lambda *a: (datetime.today()-relativedelta(day=1)).strftime("%Y-%m-%d")
    }

    def gen_report(self,ids,context={}):
        obj=self.browse(ids[0])
        date_from=obj.date_from
        get_model("sale.order").gen_report(date_from)

GenReport.register()
