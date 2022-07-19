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
from netforce import access


class StockConsignPeriod(Model):
    _name = "stock.consign.period"
    _string = "Consignment Period"
    _fields = {
        "consign_id": fields.Many2One("stock.consign","Consignment Stock",required=True,on_delete="cascade"),
        "date_from": fields.Date("From Date",required=True),
        "date_to": fields.Date("To Date",required=True),
        "use_qty": fields.Decimal("Issued Qty",function="get_use",function_multi=True),
        "use_amount": fields.Decimal("Issued Cost",function="get_use",function_multi=True),
        "sale_qty": fields.Decimal("Sales Qty",function="get_use",function_multi=True),
        "sale_amount": fields.Decimal("Sales Amount",function="get_use",function_multi=True),
        "sale_id": fields.Many2One("sale.order","Sales Order"),
        "purchase_id": fields.Many2One("purchase.order","Purchase Order"),
    }
    _order="date_from desc"

    def get_use(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            use_qty=0
            use_amt=0
            for move in get_model("stock.move").search_browse([["location_from_id","=",obj.consign_id.location_id.id],["location_to_id.type","=","customer"],["date",">=",obj.date_from+" 00:00:00"],["date","<=",obj.date_to+" 23:59:59"],["state","=","done"]]):
                use_qty+=move.qty # XXX: uom
                use_amt+=move.qty*(move.product_id.purchase_price or 0) # XXX: currency
            sale_qty=0
            sale_amt=0
            for line in get_model("sale.order.line").search_browse([["location_id","=",obj.consign_id.location_id.id],["date",">=",obj.date_from],["date","<=",obj.date_to],["state","in",("confirmed","done")]]):
                if line.qty_delivered<line.qty:
                    continue
                sale_qty+=line.qty # XXX: uom
                sale_amt+=line.amount # XXX: currency
            vals[obj.id]={
                "use_qty": use_qty,
                "use_amount": use_amt,
                "sale_qty": sale_qty,
                "sale_amount": sale_amt,
            }
        return vals

    def create_purchase(self,ids,context={}):
        for obj in self.browse(ids):
            vals={
                "company_id": obj.consign_id.company_id.id,
                "contact_id": obj.consign_id.contact_id.id,
                "lines": [],
            }
            if obj.consign_id.order_type=="stock":
                prod_qtys={}
                for move in get_model("stock.move").search_browse([["location_from_id","=",obj.consign_id.location_id.id],["location_to_id.type","=","customer"],["date",">=",obj.date_from+" 00:00:00"],["date","<=",obj.date_to+" 23:59:59"],["state","=","done"]]):
                    prod_id=move.product_id.id
                    prod_qtys.setdefault(prod_id,0)
                    prod_qtys[prod_id]+=move.qty # XXX: uom
                for prod_id,qty in prod_qtys.items():
                    prod=get_model("product").browse(prod_id)
                    price=prod.purchase_price
                    if not price and prod.parent_id:
                        price=prod.parent_id.purchase_price
                    if not price:
                        raise Exception("Missing purchase price for product %s"%prod.code)
                    line_vals={
                        "product_id": prod_id,
                        "description": prod.name,
                        "qty": qty,
                        "uom_id": prod.uom_id.id,
                        "unit_price": price,
                        "location_id": obj.consign_id.location_id.id,
                    }
                    vals["lines"].append(("create",line_vals))
            elif obj.consign_id.order_type=="sale":
                prod_qtys={}
                prom_amts={}
                for line in get_model("sale.order.line").search_browse([["location_id","=",obj.consign_id.location_id.id],["date",">=",obj.date_from],["date","<=",obj.date_to],["state","in",("confirmed","done")]]):
                    if line.qty_delivered<line.qty:
                        continue
                    prod=line.product_id
                    if not prod.id:
                        continue
                    prod_qtys.setdefault(prod.id,0)
                    prod_qtys[prod.id]+=line.qty # XXX: uom
                    if line.promotion_amount:
                        prom_ratio=line.promotion_amount/(line.amount+line.promotion_amount)
                        price=prod.purchase_price
                        if not price and prod.parent_id:
                            price=prod.parent_id.purchase_price
                        if not price:
                            raise Exception("Missing purchase price for product %s"%prod.code)
                        prom_amt=line.qty*price*prom_ratio
                        prom_amts[prod.id]=prom_amt
                for prod_id,qty in prod_qtys.items():
                    prod=get_model("product").browse(prod_id)
                    price=prod.purchase_price
                    if not price and prod.parent_id:
                        price=prod.parent_id.purchase_price
                    if not price:
                        raise Exception("Missing purchase price for product %s"%prod.code)
                    line_vals={
                        "product_id": prod_id,
                        "description": prod.name,
                        "qty": qty,
                        "uom_id": prod.uom_id.id,
                        "unit_price": price,
                        "location_id": obj.consign_id.location_id.id,
                    }
                    vals["lines"].append(("create",line_vals))
                    prom_amt=prom_amts.get(prod_id)
                    if prom_amt:
                        res=get_model("uom").search([["name","=","Unit"]])
                        if not res:
                            raise Exception("Unit uom not found")
                        uom_id=res[0]
                        line_vals={
                            "description": "Promotions for product %s"%prod.code,
                            "qty": 1,
                            "uom_id": uom_id,
                            "unit_price": -round(prom_amt,2),
                        }
                        vals["lines"].append(("create",line_vals))
            if not vals["lines"]:
                continue
            purchase_id=get_model("purchase.order").create(vals,context={"company_id":obj.consign_id.company_id.id})
            get_model("purchase.order").confirm([purchase_id])
            obj.write({"purchase_id": purchase_id})

    def create_sale(self,ids,context={}):
        for obj in self.browse(ids):
            vals={
                "company_id": obj.consign_id.company_id.id,
                "contact_id": obj.consign_id.contact_id.id,
                "lines": [],
            }
            if obj.consign_id.order_type=="stock":
                prod_qtys={}
                for move in get_model("stock.move").search_browse([["location_from_id","=",obj.consign_id.location_id.id],["location_to_id.type","=","customer"],["date",">=",obj.date_from+" 00:00:00"],["date","<=",obj.date_to+" 23:59:59"],["state","=","done"]]):
                    prod_id=move.product_id.id
                    prod_qtys.setdefault(prod_id,0)
                    prod_qtys[prod_id]+=move.qty # XXX: uom
                for prod_id,qty in prod_qtys.items():
                    prod=get_model("product").browse(prod_id)
                    price=prod.sale_price
                    if not price and prod.parent_id:
                        price=prod.parent_id.sale_price
                    if not price:
                        raise Exception("Missing sales price for product %s"%prod.code)
                    line_vals={
                        "product_id": prod_id,
                        "description": prod.name,
                        "qty": qty,
                        "uom_id": prod.uom_id.id,
                        "unit_price": price,
                        "location_id": obj.consign_id.location_id.id,
                    }
                    vals["lines"].append(("create",line_vals))
            elif obj.consign_id.order_type=="sale":
                prod_qtys={}
                prom_amts={}
                for line in get_model("sale.order.line").search_browse([["location_id","=",obj.consign_id.location_id.id],["date",">=",obj.date_from],["date","<=",obj.date_to],["state","in",("confirmed","done")],["order_id.company_id","!=",obj.consign_id.company_id.id]]):
                    prod=line.product_id
                    if not prod.id:
                        continue
                    prod_qtys.setdefault(prod.id,0)
                    prod_qtys[prod.id]+=line.qty # XXX: uom
                    if line.promotion_amount:
                        prom_ratio=line.promotion_amount/(line.amount+line.promotion_amount)
                        price=prod.sale_price
                        if not price and prod.parent_id:
                            price=prod.parent_id.sale_price
                        if not price:
                            raise Exception("Missing sales price for product %s"%prod.code)
                        prom_amt=line.qty*price*prom_ratio
                        prom_amts[prod.id]=prom_amt
                for prod_id,qty in prod_qtys.items():
                    prod=get_model("product").browse(prod_id)
                    price=prod.sale_price
                    if not price and prod.parent_id:
                        price=prod.parent_id.sale_price
                    if not price:
                        raise Exception("Missing sales price for product %s"%prod.code)
                    line_vals={
                        "product_id": prod_id,
                        "description": prod.name,
                        "qty": qty,
                        "uom_id": prod.uom_id.id,
                        "unit_price": price,
                        "location_id": obj.consign_id.location_id.id,
                    }
                    vals["lines"].append(("create",line_vals))
                    prom_amt=prom_amts.get(prod_id)
                    if prom_amt:
                        res=get_model("uom").search([["name","=","Unit"]])
                        if not res:
                            raise Exception("Unit uom not found")
                        uom_id=res[0]
                        line_vals={
                            "description": "Promotions for product %s"%prod.code,
                            "qty": 1,
                            "uom_id": uom_id,
                            "unit_price": -round(prom_amt,2),
                        }
                        vals["lines"].append(("create",line_vals))
            if not vals["lines"]:
                continue
            sale_id=get_model("sale.order").create(vals,context={"company_id":obj.consign_id.company_id.id})
            get_model("sale.order").confirm([sale_id])
            obj.write({"sale_id": sale_id})

StockConsignPeriod.register()
