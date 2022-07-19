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
try:
    from simpleeval import simple_eval
except:
    raise Exception("Failed to import simpleeval")
from datetime import *
from dateutil.relativedelta import *

def get_month(date=None,delta=None):
    if date:
        d=datetime.strptime(date,"%Y-%m-%d")
    else:
        d=datetime.today()
    if delta:
        d+=relativedelta(months=delta)
    return d.strftime("%Y-%m")

def get_date_range(date):
    if not date:
        return [None,None]
    if len(date)==10:
        return [None,date]
    if len(date)==7:
        date_from=date+"-01"
        date_to=(datetime.strptime(date_from,"%Y-%m-%d")+relativedelta(day=31)).strftime("%Y-%m-%d")
        return [date_from,date_to]

def bal(acc_code,date=None):
    res=get_model("account.account").search([["code","=",acc_code]])
    if not res:
        raise Exception("Account code not found: %s"%acc_code)
    acc_id=res[0]
    date_from,date_to=get_date_range(date)
    ctx={
        "date_from": date_from,
        "date_to": date_to,
    }
    acc=get_model("account.account").browse(acc_id,context=ctx)
    return acc.balance

def qty(prod_code):
    res=get_model("product").search([["code","=",prod_code]])
    if not res:
        raise Exception("Product code not found: %s"%prod_code)
    prod_id=res[0]
    qty=get_model("stock.balance").get_prod_qty(prod_id)
    return qty

def qty_categ(categ_code,loc_code):
    res=get_model("product.categ").search([["code","=",categ_code]])
    if not res:
        raise Exception("Product category code not found: %s"%categ_code)
    categ_id=res[0]
    prod_ids=get_model("product").search([["categ_id","child_of",categ_id]])
    res=get_model("stock.location").search([["code","=",loc_code]])
    if not res:
        raise Exception("Location code not found: %s"%loc_code)
    loc_id=res[0]
    qty=get_model("stock.balance").get_qty_multi(prod_ids,[loc_id])
    return qty

def skus_categ(categ_code,loc_code):
    res=get_model("product.categ").search([["code","=",categ_code]])
    if not res:
        raise Exception("Product category code not found: %s"%categ_code)
    categ_id=res[0]
    prod_ids=get_model("product").search([["categ_id","child_of",categ_id]])
    res=get_model("stock.location").search([["code","=",loc_code]])
    if not res:
        raise Exception("Location code not found: %s"%loc_code)
    loc_id=res[0]
    qty=get_model("stock.balance").get_skus_multi(prod_ids,[loc_id])
    return qty

INCOME_TYPES = ["revenue", "other_income"]
GROSS_PROFIT_TYPES = ["revenue", "cost_sales", "other_income"]
NET_INCOME_TYPES = ["revenue", "cost_sales", "other_income", "expense", "other_expense"]

def income_year(track_code):
    date_from = date.today().strftime("%Y-01-01")
    date_to = date.today().strftime("%Y-12-31")
    res=get_model("account.track.categ").search([["code","=",track_code]])
    if not res:
        raise Exception("Invalid tracking category: %s"%track_code)
    track_id=res[0]
    cond=[["type","in",INCOME_TYPES]]
    ctx={
        "date_from": date_from,
        "date_to": date_to,
        "track_id": track_id,
    }
    accounts=get_model("account.account").search_browse(cond,context=ctx)
    bal=0
    for acc in accounts: 
        bal+=acc.balance
    return -bal

def income_month(track_code,month):
    print("income_month",track_code,month)
    date_from = date.today().strftime("%%Y-%d-01"%(month+1))
    print("date_from",date_from)
    date_to=(datetime.strptime(date_from,"%Y-%m-%d")+relativedelta(day=31)).strftime("%Y-%m-%d")
    print("date_to",date_to)
    res=get_model("account.track.categ").search([["code","=",track_code]])
    if not res:
        raise Exception("Invalid tracking category: %s"%track_code)
    track_id=res[0]
    cond=[["type","in",INCOME_TYPES]]
    ctx={
        "date_from": date_from,
        "date_to": date_to,
        "track_id": track_id,
    }
    accounts=get_model("account.account").search_browse(cond,context=ctx)
    bal=0
    for acc in accounts: 
        bal+=acc.balance
    return -bal

def income_year_percent(track_code):
    return 0

def income_month_percent(track_code,month):
    return 0

def gross_profit_year(track_code):
    print("gross_profit_year",track_code)
    date_from = date.today().strftime("%Y-01-01")
    date_to = date.today().strftime("%Y-12-31")
    res=get_model("account.track.categ").search([["code","=",track_code]])
    if not res:
        raise Exception("Invalid tracking category: %s"%track_code)
    track_id=res[0]
    cond=[["type","in",GROSS_PROFIT_TYPES]]
    ctx={
        "date_from": date_from,
        "date_to": date_to,
        "track_id": track_id,
    }
    accounts=get_model("account.account").search_browse(cond,context=ctx)
    bal=0
    for acc in accounts: 
        bal+=acc.balance
    return -bal

def gross_profit_month(track_code,month):
    print("gross_profit_month",track_code,month)
    date_from = date.today().strftime("%%Y-%d-01"%(month+1))
    print("date_from",date_from)
    date_to=(datetime.strptime(date_from,"%Y-%m-%d")+relativedelta(day=31)).strftime("%Y-%m-%d")
    print("date_to",date_to)
    res=get_model("account.track.categ").search([["code","=",track_code]])
    if not res:
        raise Exception("Invalid tracking category: %s"%track_code)
    track_id=res[0]
    cond=[["type","in",GROSS_PROFIT_TYPES]]
    ctx={
        "date_from": date_from,
        "date_to": date_to,
        "track_id": track_id,
    }
    accounts=get_model("account.account").search_browse(cond,context=ctx)
    bal=0
    for acc in accounts: 
        bal+=acc.balance
    return -bal

def net_income_year(track_code):
    print("net_income_year",track_code)
    date_from = date.today().strftime("%Y-01-01")
    date_to = date.today().strftime("%Y-12-31")
    res=get_model("account.track.categ").search([["code","=",track_code]])
    if not res:
        raise Exception("Invalid tracking category: %s"%track_code)
    track_id=res[0]
    cond=[["type","in",NET_INCOME_TYPES]]
    ctx={
        "date_from": date_from,
        "date_to": date_to,
        "track_id": track_id,
    }
    accounts=get_model("account.account").search_browse(cond,context=ctx)
    bal=0
    for acc in accounts: 
        bal+=acc.balance
    return -bal

def net_income_month(track_code,month):
    print("net_income_month",track_code,month)
    date_from = date.today().strftime("%%Y-%d-01"%(month+1))
    print("date_from",date_from)
    date_to=(datetime.strptime(date_from,"%Y-%m-%d")+relativedelta(day=31)).strftime("%Y-%m-%d")
    print("date_to",date_to)
    res=get_model("account.track.categ").search([["code","=",track_code]])
    if not res:
        raise Exception("Invalid tracking category: %s"%track_code)
    track_id=res[0]
    cond=[["type","in",NET_INCOME_TYPES]]
    ctx={
        "date_from": date_from,
        "date_to": date_to,
        "track_id": track_id,
    }
    accounts=get_model("account.account").search_browse(cond,context=ctx)
    bal=0
    for acc in accounts: 
        bal+=acc.balance
    return -bal

def net_income_year_percent(track_code):
    return 0

def net_income_month_percent(track_code,month):
    return 0

def sale_target_year(track_code):
    print("sale_target_year",track_code)
    date_from = date.today().strftime("%Y-01-01")
    date_to = date.today().strftime("%Y-12-31")
    res=get_model("account.track.categ").search([["code","=",track_code]])
    if not res:
        raise Exception("Invalid tracking category: %s"%track_code)
    track_id=res[0]
    target_ids=get_model("sale.target").search([["date_from","<=",date_to],["date_to",">=",date_from],["track_id","=",track_id]])
    amt=0
    for target in get_model("sale.target").browse(target_ids):
        amt+=target.amount_target or 0
    return amt

def sale_target_month(track_code,month):
    print("sale_target_month",track_code,month)
    date_from = date.today().strftime("%%Y-%d-01"%(month+1))
    date_to=(datetime.strptime(date_from,"%Y-%m-%d")+relativedelta(day=31)).strftime("%Y-%m-%d")
    res=get_model("account.track.categ").search([["code","=",track_code]])
    if not res:
        raise Exception("Invalid tracking category: %s"%track_code)
    track_id=res[0]
    target_ids=get_model("sale.target").search([["date_from","<=",date_to],["date_to",">=",date_from],["track_id","=",track_id]])
    amt=0
    for target in get_model("sale.target").browse(target_ids):
        amt+=target.amount_target or 0
    return amt

FUNCTIONS={
    "GET_MONTH": get_month,
    "BAL": bal,
    "QTY": qty,
    "QTY_CATEG": qty_categ,
    "SKUS_CATEG": skus_categ,
    "INCOME_YEAR": income_year,
    "INCOME_MONTH": income_month,
    "GROSS_PROFIT_YEAR": gross_profit_year,
    "GROSS_PROFIT_MONTH": gross_profit_month,
    "INCOME_YEAR_PERCENT": income_year_percent,
    "INCOME_MONTH_PERCENT": income_month_percent,
    "NET_INCOME_YEAR": net_income_year,
    "NET_INCOME_MONTH": net_income_month,
    "NET_INCOME_YEAR_PERCENT": net_income_year_percent,
    "NET_INCOME_MONTH_PERCENT": net_income_month_percent,
    "SALE_TARGET_YEAR": sale_target_year,
    "SALE_TARGET_MONTH": sale_target_month,
}

class ReportTemplate(Model):
    _name = "report.template"
    _string = "Report Template"
    _multi_company = True
    _audit_log = True
    _fields = {
        "name": fields.Char("Template Name", required=True, search=True),
        "type": fields.Selection([
            ["cust_invoice", "Customer Invoice"],
            ["cust_credit_note", "Customer Credit Note"],
            ["supp_invoice", "Supplier Invoice"],
            ["payment", "Payment"],
            ["account_move", "Journal Entry"],
            ["sale_quot", "Quotation"],
            ["sale_order", "Sales Order"],
            ["sale_return", "Sales Return"],
            ["purch_order", "Purchase Order"],
            ["purchase_request", "Purchase Request"],
            ["prod_order", "Production Order"],
            ["goods_receipt", "Goods Receipt"],
            ["goods_transfer", "Goods Transfer"],
            ["goods_issue", "Goods Issue"],
            ["stock_move", "Stock Movement"],
            ["pay_slip", "Pay Slip"],
            ["tax_detail", "Tax Detail"],
            ["expense_claim", "Expense Claim"],
            ["landed_cost", "Landed Cost"],
            ["delivery_route","Delivery Route"],
            ["other", "Other"]], "Template Type", required=True, search=True),
        "format": fields.Selection([["jsx","JSX"], ["hbs","HBS"], ["odt", "ODT"], ["docx", "DOCX"], ["xlsx", "XLSX"], ["jrxml", "JRXML"], ["nfjson","NFJSON"]], "Template Format", required=True, search=True),
        "file": fields.File("Template File"),
        "body": fields.Text("Template Body"),
        "orientation": fields.Selection([["portrait","Portrait"],["landscape","Landscape"]],"Orientation"),
        "printer_name": fields.Char("Printer Name"),
        "company_id": fields.Many2One("company", "Company"),
        "field_names": fields.Text("Template Fields"),
        "convert_pdf": fields.Boolean("Convert To PDF"),
        "multi_render": fields.Boolean("Multi Render"),
        "sequence": fields.Integer("Sequence"),
        "out_filename": fields.Char("Output Filename"),
        "header": fields.Text("Header"),
        "footer": fields.Text("Footer"),
        "logs": fields.One2Many("log","related_id","Logs"),
        "model_id": fields.Many2One("model","Model"),
        "user_id": fields.Many2One("base.user","Created By"),
    }
    _order="type,sequence,name"
    _defaults={
        "user_id": lambda *a: access.get_active_user(),
    }

    def new_template_nfjson(self,name,template_type=None,model=None,context={}):
        if model:
            res=get_model("model").search([["name","=",model]])
            if not res:
                raise Exception("Invalid model: %s"%model)
            model_id=res[0]
        else:
            model_id=None
        vals={
            "name": name,
            "type": template_type or "other",
            "model_id": model_id,
            "format": "nfjson",
        }
        new_id=self.create(vals)
        return {
            "template_id": new_id,
        }

    def eval_formulas(self, formulas, context={}):
        access.set_active_user(1) # XXX
        access.set_active_company(1) # XXX
        vals={}
        for formula in formulas:
            vals[formula]=self.eval_formula(formula,context=context)
        return vals

    def get_report_functions(self,context={}):
        return FUNCTIONS

    def eval_formula(self, formula, context={}):
        print("eval_formula",formula)
        try:
            functions=self.get_report_functions()
            def _get_field_value(name):
                vals=context.get("field_values",{})
                return vals.get(name)
            functions["FIELD"]=_get_field_value
            val=simple_eval(formula,functions=functions,names=context)
        except Exception as e:
            val="Error: %s"%e
        print("=> val=%s"%val)
        return val

ReportTemplate.register()
