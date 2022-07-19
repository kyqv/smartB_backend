from netforce.model import Model, fields, get_model
from datetime import *
from dateutil.relativedelta import *
from netforce import database
from netforce.access import get_active_company
from pprint import pprint


class ReportSaleCommission(Model):
    _name = "report.sale.commission"
    _transient = True
    _fields = {
        "date_from": fields.Date("Date From"),
        "date_to": fields.Date("Date To"),
        "seller_percent": fields.Decimal("Seller %"),
        "parent_percent": fields.Decimal("Seller Parent %"),
        "grand_parent_percent": fields.Decimal("Seller Grand Parent %"),
        "default_margin": fields.Decimal("Default Profit Margin %"),
    }
    _defaults = {
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today() + relativedelta(day=31)).strftime("%Y-%m-%d"),
        "seller_percent": 20,
        "parent_percent": 20,
        "grand_parent_percent": 10,
    }

    def get_report_data(self, ids, context={}):
        if not ids:
            return
        company_id = get_active_company()
        settings = get_model("settings").browse(1)
        obj=self.browse(ids[0])
        date_from = obj.date_from
        date_to = obj.date_to
        data={
            "date_from": date_from,
            "date_to": date_to,
        }
        cond=[["order_id.date",">=",date_from],["order_id.date","<=",date_to],["state","in",["confirmed","done"]]]
        tot_profit=0
        tot_seller={}
        tot_parent={}
        tot_grand_parent={}
        det_seller={}
        det_parent={}
        det_grand_parent={}
        for line in get_model("sale.order.line").search_browse(cond):
            contact=line.order_id.seller_contact_id
            if not contact:
                continue
            prod=line.product_id
            if not prod:
                continue
            purch_price=prod.purchase_price
            if purch_price:
                profit=(line.unit_price-purch_price)*line.qty
            else:
                profit=(line.unit_price*(obj.default_margin or 0)/100)*line.qty
            tot_profit+=profit
            tot_seller.setdefault(contact.id,0)
            tot_seller[contact.id]+=profit*(obj.seller_percent or 0)/100
            det_seller.setdefault(contact.id,[]).append({
                "sale_no": line.order_id.number,
                "sale_id": line.order_id.id,
                "prod_name": prod.name,
                "qty": line.qty,
                "sale_price": line.unit_price,
                "purch_price": purch_price,
                "profit": profit,
                "com_amt": profit*(obj.seller_percent or 0)/100,
                "level": "1",
            })
            parent=contact.commission_parent_id
            if parent:
                tot_parent.setdefault(parent.id,0)
                tot_parent[parent.id]+=profit*(obj.parent_percent or 0)/100
                det_parent.setdefault(parent.id,[]).append({
                    "sale_no": line.order_id.number,
                    "sale_id": line.order_id.id,
                    "prod_name": prod.name,
                    "qty": line.qty,
                    "sale_price": line.unit_price,
                    "purch_price": purch_price,
                    "profit": profit,
                    "com_amt": profit*(obj.parent_percent or 0)/100,
                    "level": "2",
                    "seller_name": contact.name, 
                })
                g_parent=parent.commission_parent_id
                if g_parent:
                    tot_grand_parent.setdefault(g_parent.id,0)
                    tot_grand_parent[g_parent.id]+=profit*(obj.grand_parent_percent or 0)/100
                    det_grand_parent.setdefault(g_parent.id,[]).append({
                        "sale_no": line.order_id.number,
                        "sale_id": line.order_id.id,
                        "prod_name": prod.name,
                        "qty": line.qty,
                        "sale_price": line.unit_price,
                        "purch_price": purch_price,
                        "profit": profit,
                        "com_amt": profit*(obj.grand_parent_percent or 0)/100,
                        "level": "3",
                        "seller_name": contact.name, 
                    })
        contact_ids=list(tot_seller.keys())
        contact_ids+=list(tot_parent.keys())
        contact_ids+=list(tot_grand_parent.keys())
        contact_ids=list(set(contact_ids))
        lines=[]
        details=[]
        for contact in get_model("contact").browse(contact_ids):
            amt_seller=tot_seller.get(contact.id,0)
            amt_parent=tot_parent.get(contact.id,0)
            amt_grand_parent=tot_grand_parent.get(contact.id,0)
            lines.append({
                "contact_name": contact.name,
                "contact_code": contact.code,
                "amount_seller": amt_seller,
                "amount_parent": amt_parent,
                "amount_grand_parent": amt_grand_parent,
                "amount": amt_seller+amt_parent+amt_grand_parent,
            })
            for d in det_seller.get(contact.id,[]):
                d.update({
                    "contact_name": contact.name,
                    "contact_code": contact.code,
                })
                details.append(d)
            for d in det_parent.get(contact.id,[]):
                d.update({
                    "contact_name": contact.name,
                    "contact_code": contact.code,
                })
                details.append(d)
            for d in det_grand_parent.get(contact.id,[]):
                d.update({
                    "contact_name": contact.name,
                    "contact_code": contact.code,
                })
                details.append(d)
        lines.sort(key=lambda l: l["contact_name"])
        details.sort(key=lambda l: l["contact_name"])
        tot_com=sum(l["amount"] for l in lines)
        data["lines"]=lines
        data["details"]=details
        data["profit"]=tot_profit
        data["total_commission"]=tot_com
        data["profit_remain"]=tot_profit-tot_com
        print("data")
        pprint(data)
        return data

ReportSaleCommission.register()
