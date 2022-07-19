from netforce.model import Model, fields, get_model
from netforce import access
from netforce import database
from datetime import *
from dateutil.relativedelta import *
import time
import io
from pprint import pprint

class ReportStockExpire(Model):
    _name = "report.stock.expire"
    _transient = True
    _fields = {
        "date": fields.Date("Date", required=True),
        "forecast_days": fields.Integer("Forecast Days",required=True),
        "product_id": fields.Many2One("product", "Product", on_delete="cascade"),
    }
    _defaults = {
        "date": lambda *a: date.today().strftime("%Y-%m-%d"),
        "forecast_days": 180,
    }

    def get_report_data(self, ids, context={}):
        print("forecast_summary.get_report_data")
        company_id = access.get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        date = params.get("date")
        if not date:
            return
        d=datetime.strptime(date,"%Y-%m-%d")
        months=[]
        for i in range(12):
            months.append({
                "month_name": d.strftime("%b %Y"),
            })
            d+=relativedelta(months=1)
        prod_ids=[]
        for bal in get_model("stock.balance").search_browse([]):
            prod=bal.product_id
            prod_ids.append(prod.id)
        prod_ids=list(set(prod_ids))
        lines=[]
        for prod in get_model("product").browse(prod_ids):
            line={
                "prod_code": prod.code,
                "prod_name": prod.name,
                "months": [],
            }
            for i in range(12):
                month={
                    "exp_qty": 0,
                }
                line["months"].append(month)
            lines.append(line)
        lines.sort(key=lambda l: l["prod_code"])
        return {
            "company_name": comp.name,
            "date": date,
            "months": months,
            "lines": lines,
        }

ReportStockExpire.register()
