from netforce.model import Model, fields, get_model
from datetime import *
from dateutil.relativedelta import *
from netforce import database
from netforce.access import get_active_company


class ReportSaleProfitDetails(Model):
    _name = "report.sale.profit.details"
    _transient = True
    _fields = {
        "sale_id": fields.Many2One("sale.order","Sales Order",required=True,on_delete="cascade"),
    }

    def get_report_data(self, ids, context={}):
        company_id = get_active_company()
        comp = get_model("company").browse(company_id)
        if ids:
            params = self.read(ids, load_m2o=False)[0]
        else:
            params = self.default_get(load_m2o=False, context=context)
        settings = get_model("settings").browse(1)
        sale_id = params.get("sale_id")
        if not sale_id:
            return
        sale=get_model("sale.order").browse(sale_id)
        lines = []
        for line in sale.lines:
            line = {
                "sequence": line.description,
                "description": line.description,
                "qty": line.qty,
                "uom_name": line.uom_id.name if line.uom_id else None,
                "unit_price": line.unit_price,
                "amount": line.amount,
                "cost_price": line.cost_price,
                "cost_amount": line.cost_amount,
            }
            lines.append(line)
        data = {
            "company_name": comp.name,
            "order_number": sale.number,
            "lines": lines,
        }
        return data

ReportSaleProfitDetails.register()
