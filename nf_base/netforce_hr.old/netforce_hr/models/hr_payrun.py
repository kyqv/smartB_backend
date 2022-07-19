from netforce.model import Model, fields, get_model
from datetime import *
from dateutil.relativedelta import *
from calendar import monthrange

from netforce.access import get_active_company
from netforce.utils import get_file_path

MONTHS=[
    ['1','January'],
    ['2','February'],
    ['3','March'],
    ['4','April'],
    ['5','May'],
    ['6','June'],
    ['7','July'],
    ['8','August'],
    ['9','September'],
    ['10','October'],
    ['11','November'],
    ['12','December'],
    ]

class PayRun(Model):
    _name="hr.payrun"
    _string="Pay Run"
    _name_field="number"
    _multi_company=True

    _fields={
        "number": fields.Char("Number",required=True,search=True),
        "date_from": fields.Date("From Date",required=True),
        "date_to": fields.Date("To Date",required=True),
        "date_pay": fields.Date("Pay Date",search=True),
        'month': fields.Selection(MONTHS,"Month"),
        "num_employees": fields.Integer("Employees",function="get_total",function_multi=True),
        "amount_employee": fields.Decimal("Employee Payments",function="get_total",function_multi=True),
        "amount_other": fields.Decimal("Other Payments",function="get_total",function_multi=True),
        "amount_total": fields.Decimal("Total",function="get_total",function_multi=True),
        "payslips": fields.One2Many("hr.payslip","run_id","Payslips"),
        "comments": fields.One2Many("message","related_id","Comments"),
        "company_id": fields.Many2One("company","Company"),
        "move_id": fields.Many2One("account.move","Journal Entry"),
        "state": fields.Selection([["draft","Draft"],["approved","Approved"],['paid','Paid'],['posted','Posted']],"Status",required=True),
        "department_id": fields.Many2One("hr.department","Department",search=True),
    }

    def _get_number(self,context={}):
        count=0
        while 1:
            num=get_model("sequence").get_number("payrun")
            if not num:
                num='/'.join(datetime.now().strftime("%Y-%m").split("-"))
                return num
            res=self.search([["number","=",num]])
            if not res:
                return num
            get_model("sequence").increment("payrun")
            count+=1
            if count>10:
                return "/"
    
    def _get_month(self,context={}):
        return str(int(datetime.now().strftime("%m")))

    _defaults={
        "number": _get_number,
        'month': _get_month,
        "date_from": lambda *a: date.today().strftime("%Y-%m-01"),
        "date_to": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
        "date_pay": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
        "company_id": lambda *a: get_active_company(),
        'state': 'draft',
    }

    _order="date_from desc"

    def get_total(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            num_emp=0
            amt_emp=0
            amt_other=0
            for slip in obj.payslips:
                num_emp+=1
                amt_emp+=slip.amount_net
                amt_other+=slip.amount_pay_other
            vals[obj.id]={
                "num_employees": num_emp,
                "amount_employee": amt_emp,
                "amount_other": amt_other,
                "amount_total": amt_emp+amt_other,
            }
        return vals

    def gen_payslips(self,ids,context={}):
        print("gen_payslips",ids)
        obj=self.browse(ids)[0]
        date_from=obj.date_from
        date_to=obj.date_to
        date_pay=obj.date_pay
        dom=[["work_status","=","working"]]
        dom2=[["run_id","=",obj.id]]
        if obj.department_id:
            dom.append(['department_id','=',obj.department_id.id]) 
            dom2.append(['department_id','=',obj.department_id.id]) 
        emp_ids=get_model("hr.employee").search(dom)
        count=0
        for emp in get_model("hr.employee").browse(emp_ids):
            if emp.hire_date <= date_to and emp.work_status in ("working"):
                count+=1
                dom3=[d for d in dom2]
                dom3.append(["employee_id","=",emp.id])
                exist_payslips=get_model("hr.payslip").search_browse(dom3)
                to_date = obj.date_to
                hire_date=emp.hire_date
                hire_year,hire_month,hire_day=hire_date.split("-")
                to_year,to_month,to_day=to_date.split("-")
                to_month=int(to_month)
                to_year=int(to_year)
                hire_month=int(hire_month)
                hire_year=int(hire_year)
                hire_day=int(hire_day)
                resign_date = emp.resign_date
                if resign_date:
                    resign_year,resign_month,resign_day=resign_date.split("-")
                    resign_day = int(resign_day)
                    resign_year = int(resign_year)
                    resign_month = int(resign_month)
                period = 13 - to_month
                if exist_payslips:
                    continue
                vals={
                    "employee_id": emp.id,
                    "date_from": date_from,
                    "date_to": date_to,
                    'due_date': date_pay or date_to,
                    "run_id": obj.id,
                    'company_id': get_active_company(),
                }
                if obj.department_id:
                    vals['department_id']=obj.department_id.id
                lines=[]
                ctx={
                    "employee_id": emp.id,
                    "date": obj.date_from,
                    "date_from": obj.date_from,
                    "date_to": obj.date_to,
                    "period": period,
                }
                for item in get_model("hr.payitem").search_browse([]): # XXX
                    # if item.tax_type=="thai":
                    #     ctx["year_income"]=(emp.salary or 0.0)*period

                    qty,rate=item.compute(context=ctx)

                    if not item.show_default:
                        continue

                    line_vals={
                        "payitem_id": item.id,
                        "qty": qty or 0,
                        "rate": rate,
                    }
                    lines.append(line_vals)
                if emp.payslip_template_id:
                    lines=[]
                    for tline in emp.payslip_template_id.lines:
                        item=tline.payitem_id
                        if hire_year == to_year and hire_month == to_month:
                            qty = tline.qty
                            salary_day = (emp.salary or 0) / 30
                            if hire_day == 1:
                                day = 30
                            elif hire_month == 2:
                                day = 29 - hire_day
                            elif hire_month in (4,6,9,11):
                                day = 31 - hire_day
                            else:
                                day = 32 - hire_day
                            salary = salary_day * day
                            context['salary_first'] = salary
                            context['employee_id'] = emp.id
                            if item.type == "wage" and item.wage_type == "salary":
                                rate = salary
                            elif item.type == "deduct" and item.deduct_type == "thai_social":
                                rate = get_model("hr.payitem").compute_thai_social(context=context)
                            elif item.type == "contrib" and item.contrib_type == "sso":
                                rate = get_model("hr.payitem").compute_thai_social_accu(context=context)
                            elif item.type == "deduct" and item.deduct_type == "provident":
                                rate = get_model("hr.payitem").compute_provident(context=context)
                            elif item.type == "contrib" and item.contrib_type == "prov":
                                rate = get_model("hr.payitem").compute_provident_acc(context=context)
                            elif item.type in ("wage","allow") and item.fix_income == True and item.wage_type != "salary":
                                rate_day = tline.rate / 30
                                if hire_day == 1:
                                    day = 30
                                elif hire_month == 2:
                                    day = 29 - hire_day
                                elif hire_month in (4,6,9,11):
                                    day = 31 - hire_day
                                else:
                                    day = 32 - hire_day
                                rate = rate_day * day
                            elif item.type == "tax" and item.tax_type =="thai":
                                qty,rate=item.compute(context=ctx)
                            print("rate of .... >",rate,item.type)
                            line_vals={
                                "payitem_id": item.id,
                                "qty": qty or 0,
                                "rate": rate, #XXX
                            }
                            lines.append(line_vals)
                            continue
                        if resign_date:
                            if resign_year == to_year and resign_month == to_month:
                                qty = tline.qty
                                rate = tline.rate
                                context['salary_last'] = True
                                context['employee_id'] = emp.id
                                if item.type in ("wage","allow"):
                                    rate_day = rate / 30
                                    if resign_month == 2 and resign_day == 28 or resign_day == 29:
                                        day = 30
                                    elif resign_day > 30:
                                        day = 30
                                    else:
                                        day = resign_day
                                    rate = rate_day * day
                                elif item.type == "deduct" and item.deduct_type == "thai_social":
                                    rate = get_model("hr.payitem").compute_thai_social(context=context)
                                elif item.type == "contrib" and item.contrib_type == "sso":
                                    rate = get_model("hr.payitem").compute_thai_social_accu(context=context)
                                elif item.type == "deduct" and item.deduct_type == "provident":
                                    rate = get_model("hr.payitem").compute_provident(context=context)
                                elif item.type == "contrib" and item.contrib_type == "prov":
                                    rate = get_model("hr.payitem").compute_provident_acc(context=context)
                                if item.type == "tax" and item.tax_type =="thai":
                                    qty,rate=item.compute(context=ctx)
                                line_vals={
                                    "payitem_id": item.id,
                                    "qty": qty or 0,
                                    "rate": rate, #XXX
                                }
                                lines.append(line_vals)
                                continue
                        if item.type == "tax" and item.tax_type =="thai":
                            qty,rate=item.compute(context=ctx)
                            line_vals={
                                "payitem_id": item.id,
                                "qty": qty or 0,
                                "rate": rate, #XXX
                            }
                            lines.append(line_vals)
                            continue
                        elif item.type == "deduct" and item.deduct_type == "thai_social":
                            if emp.age >= 60:
                                rate = 0
                                qty = tline.qty
                            else:
                                qty,rate = item.compute(context=ctx)
                            line_vals={
                                "payitem_id": item.id,
                                "qty": qty or 0,
                                "rate": rate, #XXX
                            }
                            lines.append(line_vals)
                            continue
                        elif item.type == "contrib" and item.contrib_type == "sso":
                            if emp.age >= 60:
                                rate = 0
                                qty = tline.qty
                            else:
                                qty,rate = item.compute(context=ctx)
                            line_vals={
                                "payitem_id": item.id,
                                "qty": qty or 0,
                                "rate": rate, #XXX
                            }
                            lines.append(line_vals)
                            continue

                        line_vals={
                            "payitem_id": item.id,
                            "qty": tline.qty or 0,
                            "rate": (tline.rate or 0)*tline.currency_rate, #XXX
                        }
                        lines.append(line_vals)
                else:
                    emp_name = str(emp.first_name)
                    raise Exception("Missing payslip template of ",emp_name)
                vals["lines"]=[("create",line_vals) for line_vals in lines]
                get_model("hr.payslip").create(vals)
        #delete other department if exist
        if obj.department_id:
            for payslip in obj.payslips:
                if obj.department_id.id != payslip.department_id.id:
                    print("delete %s"% payslip.id)
                    payslip.delete()
        if not count:
            raise Exception("Employee is not found")
        return {
            "alert": "Payslips created successfully.",
        }

    def copy(self,ids,context):
        obj=self.browse(ids)[0]
        vals={
            "number": obj.number+"(Copy)",
            'month': obj.month,
            "date_from": obj.date_from,
            "date_to": obj.date_to,
            "date_pay": obj.date_pay,
            'department_id': obj.department_id.id,
            "payslips": [],
        }
        for payslip in obj.payslips:
            payslip_vals={
                "run_id": payslip.run_id.id,
                "employee_id": payslip.employee_id.id,
                "date_from": payslip.date_from,
                "date_to": payslip.date_to,
                "due_date": payslip.due_date,
                "state": 'draft',
                "lines": [],
            }
            for line in payslip.lines:
                line_vals={
                    "slip_id": line.slip_id.id,
                    "payitem_id": line.payitem_id.id,
                    "qty": line.qty or 0,
                    "rate": line.rate,
                    "amount": line.amount,
                }
                payslip_vals["lines"].append(("create",line_vals))

            vals["payslips"].append(("create",payslip_vals))
        new_id=self.create(vals)
        new_obj=self.browse(new_id)
        return {
            "next": {
                "name": "payrun",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "PayRun %s copied to %s"%(obj.number,new_obj.number),
        }

    def get_bank_data(self,context={}):
        ref_id=int(context.get("refer_id","0"))
        lines=[]
        obj=self.browse(ref_id)
        settings=get_model("settings").browse(1)
        symbol=settings.currency_id.code or "" 
        for payslip in obj.payslips:
            vals={
                'bank_account': payslip.employee_id.bank_account,
                'paid_amount': payslip.amount_net or 0,
            }
            lines.append(vals)
        data={
            'lines': lines,
            'symbol': symbol
        }
        return data

    def pay(self,ids,context={}):
        for obj in self.browse(ids):
            context['payrun_id']=obj.id
            for payslip in obj.payslips:
                payslip.pay(context=context)
        obj.write({
            'state': 'paid',
        })

    def approve(self,ids,context={}):
        for obj in self.browse(ids):
            for payslip in obj.payslips:
                payslip.write({
                    'state': 'approved',
                })
            obj.write({
                'state': 'approved',
            })
    
    def delete(self,ids,context={}):
        for obj in self.browse(ids):
            if obj.state!='draft':
                raise Exception("%s has been %s."%(obj.number, obj.state))
            slip_ids=[slip.id for slip in obj.payslips]
            get_model("hr.payslip").delete(slip_ids)
            if obj.move_id:
                obj.move_id.to_draft()
                for line in obj.move_id.lines:
                    line.delete()
                obj.move_id.delete()
        super().delete(ids)

    def view_journal(self,ids,context={}):
        obj=self.browse(ids)[0]
        move_id=obj.move_id
        if not move_id:
            raise Exception("#TODO Journal entry not create yet.")
        return {
            'next': {
                'name': 'journal_entry',
                'mode': 'form',
                'active_id': move_id.id,
            },
            
        }
    
    def to_draft(self,ids,context={}):
        for obj in self.browse(ids):
            for payslip in obj.payslips:
                payslip.to_draft(context=context)
            obj.write({
                'state': 'draft',
            })
    
    def get_data(self,ids,context={}):
        settings=get_model("settings").browse(1)
        pages=[]
        pages_before=[]
        for obj in self.browse(ids):
            for payslip in obj.payslips:
                context['refer_id']=payslip.id
                for _page in payslip.get_data(context=context)['pages']:
                    pages_before.append(_page)
        pages = sorted(pages_before, key=lambda x: x['emp_code'])
        if pages:
            pages[-1]["is_last_page"]=True
        return {
            "pages": pages,
            "logo": get_file_path(settings.logo),
        }

    def onchange_month(self,context={}):
        data=context['data']
        month=int(data['month'])
        year=int(date.today().strftime("%Y"))
        weekday, total_day=monthrange(int(year), int(month))
        #if not data['number']:
            #data['number']='%s/%s'%(year,(data['month'] or "").zfill(2))
        data['number']='%s/%s'%(year,(data['month'] or "").zfill(2))
        data['date_from']="%s-%s-01"%(year,month)
        data['date_to']="%s-%s-%s"%(year,month,total_day)
        data['date_pay']="%s-%s-%s"%(year,month,total_day)
        return data

    def onchange_paydate(self,context={}):
        data=context['data']
        data['date_pay']
        for payslip in data['payslips']:
            payslip['due_date']=data['date_pay']
        return data
    
    def write(self,ids,vals,**kw):
        payslip_vals={}
        if vals.get('date_from'):
            payslip_vals['date_from']=vals['date_from']
        if vals.get('date_to'):
            payslip_vals['due_date']=vals['date_to']
        if payslip_vals:
            obj=self.browse(ids)[0]
            for payslip in obj.payslips:
                payslip.write(payslip_vals)
                #TODO recompute tax
        super().write(ids,vals,**kw)

PayRun.register()
