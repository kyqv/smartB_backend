import re
from datetime import *
from dateutil.relativedelta import *
from calendar import monthrange

from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path, get_file_path
from netforce.access import get_active_company
from netforce.database import get_connection
from . import utils

class PaySlip(Model):
    _name="hr.payslip"
    _string="Pay Slip"
    _multi_company=True
    _name_field="employee_id"
    _key=['employee_id','due_date','company_id']

    def _get_currency_rate(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            crr_rate=1
            if obj.currency_id:
                crr_rate=obj.currency_id.sell_rate or 1
            res[obj.id]=crr_rate
        return res

    _fields={
        "run_id": fields.Many2One("hr.payrun","Pay Run",search=True),
        "employee_id": fields.Many2One("hr.employee","Employee",required=True,search=True ,condition=[["work_status","=","working"]]),
        "date_from": fields.Date("From",required=True,search=True),
        "date_to": fields.Date("To",required=True,search=True),
        "due_date": fields.Date("Due Date"),
        "amount_wage": fields.Decimal("Wages",function="get_total",function_multi=True),
        "amount_allow": fields.Decimal("Allowances",function="get_total_details",function_multi=True),
        "amount_deduct": fields.Decimal("Deductions",function="get_total",function_multi=True),
        "amount_income": fields.Decimal("Incomes",function="get_total",function_multi=True),
        "amount_tax": fields.Decimal("Taxes",function="get_total",function_multi=True),
        "amount_post_allow": fields.Decimal("Non-taxable Allowances",function="get_total",function_multi=True),
        "amount_post_deduct": fields.Decimal("Post-tax Deductions",function="get_total",function_multi=True),
        "amount_net": fields.Decimal("Net Pay",function="get_total",function_multi=True),
        "amount_pay_other": fields.Decimal("Other Payments",function="get_total",function_multi=True),
        "amount_salary": fields.Decimal("Salary",function="get_total_details",function_multi=True),
        "amount_bonus": fields.Decimal("Bonus",function="get_total_details",function_multi=True),
        "amount_overtime": fields.Decimal("Overtime",function="get_total_details",function_multi=True),
        "amount_social": fields.Decimal("Soc. Fund",function="get_total_details",function_multi=True),
        "amount_provident": fields.Decimal("Prov. Fund",function="get_total_details",function_multi=True),
        "amount_other_expense": fields.Decimal("Other Expense",function="get_total_details",function_multi=True),
        "amount_allow_all" : fields.Decimal("Allowances keep",function="get_total",function_multi=True),
        "lines": fields.One2Many("hr.payslip.line","slip_id","Lines"),
        "comments": fields.One2Many("message","related_id","Comments"),
        "state": fields.Selection([["draft","Draft"],["approved","Approved"],['paid','Paid'],['posted','Posted']],"Status",required=True),
        "company_id": fields.Many2One("company","Company"),
        "move_id": fields.Many2One("account.move","Journal Entry"),
        "department_id": fields.Many2One("hr.department","Department",search=True),
        "currency_id": fields.Many2One("currency","Currency"),
        "currency_rate": fields.Decimal("Currency Rate",function="_get_currency_rate",store=True), #should store because currency can change many time
    }

    def _get_currency(self,context={}):
        st=get_model('settings').browse(1)
        currency_id=st.currency_id.id
        return currency_id


    _defaults={
        "state": "draft",
        "date_from": lambda *a: date.today().strftime("%Y-%m-%d"),
        "date_to": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
        "due_date": lambda *a: (date.today()+relativedelta(day=31)).strftime("%Y-%m-%d"),
        "company_id": lambda *a: get_active_company(),
        'currency_id': _get_currency,
    }
    _sql_constraints=("hr_payslip_key_uniq","unique(employee_id,due_date,company_id)","Employee,Due Date And Company should be unique"),
    _order="run_id.date_from desc,employee_id.code,employee_id.first_name"

    def get_total(self,ids,context={}):
        all_vals={}
        for obj in self.browse(ids):
            totals={}
            total_pay_other=0
            for line in obj.lines:
                item=line.payitem_id
                t=item.type
                if t not in totals:
                    totals[t]=0
                totals[t]+=line.amount
                if t == "deduct" and item.deduct_type == "loan":
                    continue
                if t == "deduct" and item.deduct_type in ("thai_social","provident"):
                    total_pay_other+=line.amount
                if t == "tax" and item.tax_type == "thai":
                    total_pay_other+=line.amount
            vals={
                "amount_wage": totals.get("wage",0),
                "amount_allow_all": totals.get("allow",0),
                "amount_deduct": totals.get("deduct",0),
                "amount_income": totals.get("wage",0)+totals.get("allow",0),
                "amount_tax": totals.get("tax",0),
                "amount_post_allow": totals.get("post_allow",0),
                "amount_post_deduct": totals.get("post_deduct",0),
                "amount_pay_other": total_pay_other,
            }
            vals["amount_net"]=vals["amount_wage"]+vals["amount_allow_all"]-vals["amount_deduct"]-vals["amount_tax"]+vals["amount_post_allow"]-vals["amount_post_deduct"]
            all_vals[obj.id]=vals
        return all_vals

    def get_total_details(self,ids,context={}):
        all_vals={}
        for obj in self.browse(ids):
            amt_salary=0
            amt_bonus=0
            amt_overtime=0
            amt_other_expense=0
            amt_social=0
            amt_provident=0
            amt_allow=obj.amount_allow_all
            for line in obj.lines:
                item=line.payitem_id
                if item.type=="wage":
                    if item.wage_type=="salary":
                        amt_salary+=line.amount
                    elif item.wage_type=="overtime":
                        amt_overtime+=line.amount
                    elif item.wage_type=="bonus":
                        amt_bonus+=line.amount
                    elif item.wage_type=="position":
                        amt_allow+=line.amount
                    elif item.wage_type=="commission":
                        amt_allow+=line.amount
                elif item.type=="deduct":
                    if item.deduct_type=="thai_social":
                        amt_social+=line.amount
                    elif item.deduct_type=="provident":
                        amt_provident+=line.amount
                    else:
                        amt_other_expense+=line.amount
                elif item.type=="post_deduct":
                    amt_other_expense+=line.amount # XXX
            vals={
                "amount_allow": amt_allow,
                "amount_salary": amt_salary,
                "amount_bonus": amt_bonus,
                "amount_overtime": amt_overtime,
                "amount_other_expense": amt_other_expense,
                "amount_social": amt_social,
                "amount_provident": amt_provident,
            }
            all_vals[obj.id]=vals
        return all_vals

    def onchange_date(self,context={}):
        data=context["data"]
        #TODO cal date_to
        month=int(data['date_from'][5:7])
        year=int(data['date_from'][0:4])
        weekday, total_day=monthrange(int(year), int(month))
        data['date_to']='%s-%s-%s'%(str(year).zfill(4),str(month).zfill(2),str(total_day).zfill(2))
        print('data["date_to"]' , data['date_to'])
        data['due_date']=data['date_to']
        to_date = data['date_to']
        to_year,to_month,to_day=to_date.split("-")
        to_month=int(to_month)
        period = 13 - to_month
        context['period'] = period
        context['year_date']=to_date
        if data.get('employee_id'):
            self.update_amounts(context=context)
        return data

    def cal_tax(self,context={}):
        to_date = context.get("year_date") or context.get("date_to")
        employee_id = context.get("employee_id")
        income = 0
        income_sum=0
        income_first = 0
        income_last = 0
        resign_ind = False
        emp_pay=get_model('hr.employee').browse(employee_id)
        emp_id_pay =emp_pay.payslip_template_id
        hire_date = emp_pay.hire_date
        resign_date = emp_pay.resign_date
        if resign_date:
            resign_year,resign_month,resign_day=resign_date.split("-")
            resign_day = int(resign_day)
            resign_month=int(resign_month)
            resign_year=int(resign_year)
        hire_year,hire_month,hire_day=hire_date.split("-")
        hire_month=int(hire_month)
        hire_year=int(hire_year)
        hire_day=int(hire_day)
        tax_all = context.get("tax_all")
        to_year,to_month,to_day=to_date.split("-")
        to_year_start=to_year+"-01-01"
        to_year_end=to_year+"-12-31"
        to_year = int(to_year)
        to_month = int(to_month)
        no_month_to_dec = 12 - to_month
        if context.get("period"):
            period = context.get("period") 
        else:
            period = 13 - to_month
        obj2 = self.search_browse([['date_to','=',to_date],['employee_id','=',employee_id],['due_date',">=",to_year_start],['due_date','<=',to_year_end]])
        if resign_date:
            if resign_year == to_year and resign_month == to_month:
                resign_ind = True
        for obj in self.search_browse([['date_to','<=',to_date],['employee_id','=',employee_id],['due_date',">=",to_year_start],['due_date','<=',to_year_end]]):
            for line in obj.lines:
                qty=line.qty or 0
                rate=line.rate or 0
                amt=qty*rate
                item=line.payitem_id
                if item.type in ("wage","allow"): 
                    if item.fix_income == True:
                        income+=amt
                elif item.type=="deduct":
                    if item.deduct_type in ("thai_social","provident","loan"):
                        continue
                    income-=amt
        #if no_month_to_dec > 0 and emp_pay.work_status == "working":
        if emp_pay.work_status == "working":
            if resign_ind == True and obj2:
                income_sum = 0
            elif emp_id_pay:
                for payitem_line in emp_id_pay.lines:
                    qty = payitem_line.qty
                    rate = payitem_line.rate
                    if payitem_line.payitem_id.type in ("wage","allow") and payitem_line.payitem_id.fix_income == True:
                        # if payitem_line.payitem_id.wage_type == "salary":
                        if hire_year == to_year and hire_month == to_month:
                            rate_day = rate / 30
                            if hire_day == 1:
                                day = 30
                            elif hire_month == 2:
                                day = 29 - hire_day
                            elif hire_month in (4,6,9,11):
                                day = 31 - hire_day
                            else:
                                day = 32 - hire_day
                            income_first += rate_day * day * qty
                        if resign_ind == True:
                            rate_day = rate / 30
                            if resign_month == 2 and resign_day == 28 or resign_day == 29:
                                day = 30
                            elif resign_day > 30:
                                day = 30
                            else:
                                day = resign_day
                            income_last += rate_day * day
                        income_sum += qty * rate
                    elif payitem_line.payitem_id.type=="deduct":
                        if payitem_line.payitem_id.deduct_type in ("thai_social","provident","loan"):
                            continue
                        income_sum-=amt
            else:
                income_sum = emp_pay.salary
                if hire_year == to_year and hire_month == to_month:
                    rate_day = emp_pay.salary / 30
                    if hire_day == 1:
                        day = 30
                    elif hire_month == 2:
                        day = 29 - hire_day
                    elif hire_month in (4,6,9,11):
                        day = 31 - hire_day
                    else:
                        day = 32 - hire_day
                    income_first += rate_day * day
        # income = (income_sum or 0) * 12
        # context["year_income"] = income

        # if hire_year < to_year:
        #     income += (income_sum or 0) * 12
        # elif hire_year == to_year:
        #     if hire_month <= to_month:
        # print("income-------------------------------->>",income,"sum ", income_sum , income_first)
        # print("pe and no -- >",no_month_to_dec,period)
        # if resign_date:
        #     if resign_year == to_year and resign_month == to_month:
        #         income += (income_sum or 0)
        #         resign_ind = True
        #     else:
        #         if obj:
        #             income += ((income_sum or 0) * no_month_to_dec)
        #         else:
        #             income += ((income_sum or 0) * period)
        if resign_ind == True:
            income += (income_last or 0)
        else:
            if obj2:
                income += ((income_sum or 0) * no_month_to_dec)
            else:
                income += ((income_sum or 0) * period)
        if hire_year == to_year and hire_month == to_month:
            income = (income - income_sum) + income_first
            context['salary_first'] = True
        context["year_income"] = income
        # print("income --->>",income,"income sum --->",income_sum)
        tax_without = get_model("hr.payitem").compute_thai_tax_without(context=context)["A12"]
        # print("tax_all -->>",tax_all,"tax_without -->>",tax_without)
        tax_sum_before = 0
        for obj in self.search_browse([['date_to','<',to_date],['employee_id','=',employee_id],['due_date',">=",to_year_start],['due_date','<=',to_year_end]]):
            for line in obj.lines:
                qty=line.qty or 0
                rate=line.rate or 0
                amt=qty*rate
                item=line.payitem_id
                if item.type == "tax":
                    tax_sum_before += amt
        # print("tax sum before ---------->>",tax_sum_before)
        tax_keep = tax_all - tax_without
        tax_beef = tax_without - tax_sum_before
        if tax_beef > 0:
            tax_month = tax_beef/period
            tax_summary = tax_month + tax_keep
        else:
            if resign_ind == True:
                tax_summary = 0
                if tax_all > tax_sum_before:
                    tax_tax = tax_all - tax_sum_before
                    if tax_tax > 0:
                        tax_summary = tax_tax
            else:
                if tax_keep > tax_sum_before:
                    tax_summary = tax_keep - tax_sum_before
                else:
                    tax_summary = 0
        # print("tax_keep -->",tax_keep,"tax_beef -->",tax_beef,"tax_summary -->",tax_summary)
        if hire_year == to_year and hire_month == to_month:
            tax_day =  tax_summary/ 30
            if hire_day == 1:
                day = 30
            elif hire_month == 2:
                day = 29 - hire_day
            elif hire_month in (4,6,9,11):
                day = 31 - hire_day
            else:
                day = 32 - hire_day
            tax_summary = tax_day * day
        return tax_summary

    def onchange_item(self,context={}):
        data=context["data"]
        emp_id=data.get("employee_id")
        if not emp_id:
            return data
        date=data.get("date")
        emp=get_model("hr.employee").browse(emp_id)
        path=context["path"]
        line=get_data_path(data,path,parent=True)
        item_id=line["payitem_id"]
        if not item_id:
            return data
        item=get_model("hr.payitem").browse(item_id)

        hire_date=emp.hire_date
        hire_year,hire_month,hire_day=hire_date.split("-")
        to_date=data.get("date_to")
        to_year,to_month,to_day=to_date.split("-")
        to_month=int(to_month)
        to_year=int(to_year)
        hire_month=int(hire_month)
        hire_year=int(hire_year)
        period = 13 - to_month
        qty,rate=item.compute(context={"employee_id":emp_id,"date":date,"period":period,"year_date":to_date})
        if not emp.tax_register and item.type=='tax':
            line['qty'],line['rate']=0,0
            return data
        line["qty"]=qty
        line["rate"]=rate
        line["amount"]=qty*rate
        line['pay_type']=get_model('hr.payitem').get_paytype(context={'type': item.type})
        context['period']=period
        context['year_date']=to_date
        data=self.update_amounts(context=context)
        return data

    def update_amounts(self,context={}):
        print("context ====>",context)
        data=context["data"]
        lines=data['lines']
        employee_id=data["employee_id"]
        employee=get_model('hr.employee').browse(employee_id)
        date_from=data['date_from']
        year,month,day=date_from.split("-")
        date_from='-'.join([year,'01','01'])
        date_to=data['date_to']
        to_year,to_month,to_day=date_to.split("-")
        to_month=int(to_month)
        if context.get("period"):
            period = context.get("period")
        else:
            period = 13 - to_month

        if context.get("year_date"):
            year_date = context.get("year_date")
        else:
            year_date = data['date_to']

        if context.get("salary_first"):
            salary_first = context.get("salary_first")
        else:
            salary_first = False

        if context.get("salary_last"):
            salary_last = context.get("salary_last")
        else:
            salary_last = False

        ctx={
            'date_from': date_from,
            'date_to': date_to,
        }
        # get income before this month
        year_income=employee.get_income(context=ctx)
        # get income after this month until december (regular income)
        month=int(month)
        if month < 12:
            remain_month=12-month
            template=employee.payslip_template_id
            if template:
                year_income+=(template.get_income() or 0)*remain_month
        salary=0
        tax_line={}
        totals={}
        for line in lines:
            if not line:
                continue
            qty=line["qty"] or 0
            rate=line["rate"] or 0
            line["amount"]=qty*rate
            item_id=line.get("payitem_id")
            if not item_id:
                continue
            item=get_model("hr.payitem").browse(item_id)
            # get income current month
            if item.type in ('wage', 'allow'):
                year_income+=line['amount']
                if item.wage_type=='salary':
                    salary=line['amount'] 
            elif item.type=='tax' and item.tax_type=='thai':
                tax_line=line

        item_id=tax_line.get('payitem_id')
        if item_id:
            item=get_model("hr.payitem").browse(item_id)
            ctx={
                'employee_id': employee.id,
                #'year_income': year_income,
                #'salary': salary,
                'period': period,
                'year_date': year_date,
                'salary_first': salary_first,
                'salary_last': salary_last,
            }
            tax_line['qty'], tax_line['rate']=item.compute(context=ctx)
            tax_line['amount']=tax_line['qty']*tax_line['rate']

        for line in lines:
            item_id=line.get("payitem_id")
            if not item_id:
                continue
            item=get_model("hr.payitem").browse(item_id)
            t=item.type
            if t not in totals:
                totals[t]=0
            totals[t]+=line["amount"]
        data["amount_wage"]=totals.get("wage",0)
        data["amount_allow"]=totals.get("allow",0)
        data["amount_deduct"]=totals.get("deduct",0)
        data["amount_tax"]=totals.get("tax",0)
        data["amount_post_allow"]=totals.get("post_allow",0)
        data["amount_post_deduct"]=totals.get("post_deduct",0)
        data["amount_net"]=data["amount_wage"]+data["amount_allow"]-data["amount_deduct"]-data["amount_tax"]+data["amount_post_allow"]-data["amount_post_deduct"]
        return data

    def get_income(self,context):
        income=0
        if context.get('end_period',0):
            date_from="2015-01-01"
            date_to="2015-12-31"
            employee_id=context['data']['employee_id']
            for obj in self.search_browse([['date_from','>=',date_from],['date_to','<=',date_to],['employee_id','=',employee_id],['state','=','approved']]):
                for line in obj.lines:
                    qty=line.qty or 0
                    rate=line.rate or 0
                    amt=qty*rate
                    item=line.payitem_id
                    if item.type in ("wage","allow"):
                        income+=amt
                    elif item.type=="deduct":
                        if item.deduct_type in ("thai_social","provident"):
                            continue
                        income-=amt
        return income

    def _update_tax(self,context={}):
        data=context["data"]
        employee_id=data["employee_id"]
        lines=data["lines"]
        date=data['date_from']
        month=int(date[5:7])
        ctx=context.copy()
        ctx.update({'end_period':1})
        period=12
        cr_year=datetime.now().year
        employee=get_model("hr.employee").browse(employee_id)
        hire_date=employee.hire_date
        resign_date=employee.resign_date
        start_month=month-1
        # find only working month ex: just come to work this year
        if hire_date and employee.work_status=='working':
            year_hire=int(hire_date[0:4])
            month_hire=int(hire_date[5:7])
            if year_hire == cr_year:
                start_month=month_hire
                period=(period-month_hire)+1
        elif resign_date and employee.work_status=='resigned':
            year_hire=int(hire_date[0:4])
            month_hire=int(hire_date[5:7])
            if year_hire == cr_year:
                start_month=month_hire
            else:
                start_month=0
            month_resign=int(resign_date[5:7])
            period=(period-month_resign)+1
        print('start_month ', start_month)
        income=0
        salary=0
        for line in lines:
            if not line:
                continue
            qty=line.get("qty",0)
            rate=line.get("rate",0)
            amt=qty*rate
            item_id=line.get("payitem_id")

            if not item_id:
                continue

            item=get_model("hr.payitem").browse(item_id)
            if not item.include_tax and item.type!='tax':
                print('no include tax')
                continue 
            if item.type in ("wage","allow"):
                if item.wage_type and item.wage_type in ("salary"):
                    salary=amt
                else:
                    income+=amt
            elif item.type=="deduct":
                if item.deduct_type in ("thai_social","provident"):
                    continue
                income-=amt
        print(salary, period, 'income ', income, len(lines))
        for line in lines:
            if not line:
                continue
            item_id=line.get("payitem_id")
            if not item_id:
                continue
            item=get_model("hr.payitem").browse(item_id)
            if item.type=="tax":
                if item.tax_type=="thai":
                    # Compute normal rate
                    ctx={
                        "employee_id": employee_id,
                        "year_income": salary*period,
                        "period": period,
                        }
                    print('ctx ', ctx)
                    qty,rate=item.compute(context=ctx)

                    if income < 1:
                        line["qty"]=qty
                        line["rate"]=rate
                        break

                    # Init salary for each month
                    number_month=12
                    salary_line=[n >= start_month and salary or 0 for n in list(range(number_month+1))]
                    print('salary_line ', salary_line)
                    irr_line=[0 for s in salary_line]
                    irr_line[month]=income
                    # Init tax_year for each month
                    tax_line=[0 for s in salary_line]
                    print('tax_line ', tax_line)
                    # Store regular tax
                    tax_line[0]=rate*period

                    #cr_year=datetime.now().year
                    start_date=str(cr_year)+'-01-01'
                    stop_date=str(cr_year)+'-12-31'

                    dom=[
                        ['date_from','>=',start_date],
                        ['date_to','<=',stop_date],
                        ['employee_id','=',employee_id],
                    ]
                    print('dom ', dom)

                    # January
                    count=start_month or 1
                    print('start_month ', start_month)
                    for obj in self.search_browse(dom,order="date_from"):
                        if count > 12:
                            continue
                        obj_month=int(obj.date_from[5:7])
                        # compute only previous month
                        if obj_month >= month:
                            print('skip %s' % (month))
                            break
                        for obj_line in obj.lines:
                            obj_item=obj_line.payitem_id
                            amt=obj_line.qty*obj_line.rate
                            if obj_item.type in ('wage', 'allow'):
                                wage_type=obj_item.wage_type or ""
                                if wage_type and wage_type in ('salary'):
                                    salary_line[count]=amt
                                else:
                                    irr_line[count]+=amt
                                    print(count,' ---> ',amt)
                            elif obj_item.type in ('deduct'):
                                if obj_item.deduct_type in ("thai_social","provident"):
                                    continue
                                irr_line[count]-=amt
                        count+=1
                    def get_salary_year(line):
                        period=len(line)
                        for i in range(period):
                            # jan-dec
                            if i > 0:
                                bf=sum(line[1:i])
                                it=line[i]*(period-i)
                                yield bf+it

                    salary_line=[0]+list(get_salary_year(salary_line))
                    # Total of income & irr income for each month
                    income_line=list(map(lambda x: sum(x), list(zip(salary_line,irr_line))))
                    count=1
                    irr_amt=0
                    ctx['period']=period
                    print('period ', period)
                    print('income_line --> ', income_line)
                    print('irr_line --> ', irr_line)
                    print('tax_line --> ', tax_line)
                    for income in income_line:
                        irr_amt+=irr_line[count-1]
                        ctx["year_income"]=income and income + irr_amt or -1 # FIXME get_yearly_income
                        qty,rate=item.compute(context=ctx)
                        tax_line[count]=(rate*period)
                        count+=1
                
                    regular_tax=tax_line[0]/period
                    rate=tax_line[month]-tax_line[month-1]+regular_tax
                    print(' ------------ summary --------- ')
                    print('tax_line ', tax_line[month], tax_line[month-1], regular_tax)
                    print('final rate ', rate)
                    line["qty"]=1
                    line["rate"]=rate
        return data

    def onchange_employee(self,context={}):
        data=context["data"]
        to_date=data.get("date_to")
        emp_id=data.get("employee_id")
        if not emp_id:
            return
        date=data.get("date_from")
        if not date:
            return

        emp=get_model("hr.employee").browse(emp_id)
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
        # if hire_year < to_year:
        #     period = 12
        # elif hire_year == to_year:
        period = 13 - to_month

        lines=[]
        for item in get_model("hr.payitem").search_browse([]):
            ctx={
                "employee_id": emp_id,
                "date": date,
                "year_date": to_date,
                "period": period,
            }
            qty,rate=item.compute(context=ctx)
            if not item.show_default:
                continue
            line={
                "payitem_id": item.id,
                "qty": qty,
                "rate": rate,
            }
            lines.append(line)
        emp_pay=get_model('hr.employee').browse(emp_id)
        emp_id_pay =emp_pay.payslip_template_id
        if emp_id_pay.id:
            lines=[]
            for payitem_line in emp_id_pay.lines:
                item=payitem_line.payitem_id
                qty=payitem_line.qty or 0
                rate=payitem_line.rate or 0
                if hire_year == to_year and hire_month == to_month:
                    salary_day = emp.salary / 30
                    if hire_day == 1:
                        day = 30
                    elif hire_month == 2:
                        day = 29 - hire_day
                    elif hire_month in (4,6,9,11):
                        day = 31 - hire_day
                    else:
                        day = 32 - hire_day
                    salary = salary_day * day
                    context['salary_first'] = True
                    context['employee_id'] = emp_id
                    if item.type == "wage" and item.wage_type == "salary":
                        rate = salary
                    elif item.type == "deduct" and item.deduct_type == "thai_social":
                        rate = get_model("hr.payitem").compute_thai_social(context=context)
                    elif item.type == "contrib" and item.contrib_type == "sso":
                        rate = get_model("hr.payitem").compute_thai_social_accu(context=context)
                    if item.type in ("wage","allow") and item.fix_income == True and item.wage_type != "salary":
                        rate_day = rate / 30
                        if hire_day == 1:
                            day = 30
                        elif hire_month == 2:
                            day = 29 - hire_day
                        elif hire_month in (4,6,9,11):
                            day = 31 - hire_day
                        else:
                            day = 32 - hire_day
                        rate = rate_day * day

                if resign_date:
                    if resign_year == to_year and resign_month == to_month:
                        context['employee_id'] = emp_id
                        context['salary_last'] = True
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
                line={
                    "payitem_id": item.id,
                    "qty": qty,
                    "rate": rate,
                }
                lines.append(line)
        for line in lines:
            item_id=line['payitem_id']
            item=get_model("hr.payitem").browse(item_id)
            line['pay_type']=get_model("hr.payitem").get_paytype(context={'type': item.type})
        data["lines"]=lines
        data['department_id']=emp.department_id.id
        context['year_date']=to_date
        context['period']=period
        self.update_amounts(context=context)
        return data

    def approve(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state":"approved"})
        flash='Payslip has been approved'
        if len(ids) > 1:
            flash='payslips has been approved'
        return {
            "action":{
                "name":"payslip"
            },
            "flash": flash,
        }

    def merge_lines(self,lines=[]):
        account={}
        for line in lines:
            desc=line['description']
            acc_id=line['account_id']
            debit=line['debit'] or 0
            credit=line['credit'] or 0
            if acc_id not in account.keys():
                account[acc_id]={
                    'account_id': acc_id,
                    'description': desc,
                    'debit': debit,
                    'credit': credit,
                }
                continue
            account[acc_id]['debit']+=debit
            account[acc_id]['credit']+=credit
        nlines=[]
        for acc_id, vals in account.items():
            nlines.append(vals)
        return nlines

    def get_move_lines(self,ids,context={}):
        #step
        # 1. set debit/credit amount
        # 2. group account code
        # 3. order by debit, credit
        lines=[]
        for obj in self.browse(ids):
            total_credit=0
            total_debit=0
            for line in obj.lines:
                item=line.payitem_id
                account=item.account_id
                amount=line.amount or 0
                if account and amount:
                    vals={
                        'description': item.name or "",
                        'account_id': account.id,
                        'debit': 0,
                        'credit': 0,
                        'contrib': False,
                    }
                    acc_type=item.acc_type
                    if item.type=='contrib':
                        vals['contrib']=True
                        if acc_type =='debit':
                            vals['debit']=amount
                        else:
                            vals['credit']=amount
                    else:
                        if acc_type =='debit':
                            vals['debit']=amount
                            total_debit+=amount
                        else:
                            vals['credit']=amount
                            total_credit+=amount
                    if vals['credit'] or vals['debit']:
                        lines.append(vals)
            #add so, prov acc
            pst=get_model("hr.payroll.settings").browse(1)
            bank_account_id=pst.bank_account_id
            if bank_account_id:
                    vals={
                        'description': bank_account_id.name or "",
                        'account_id': bank_account_id.id,
                        'debit': 0,
                        'credit': obj.amount_net or 0,
                    }
                    lines.append(vals)
        return sorted(self.merge_lines(lines), key=lambda x: x['credit'])

    def pay(self,ids,context={}):
        #payrun_id=context.get('payrun_id')
        for obj in self.browse(ids):
            obj.write({
                "state":"paid",
                })
            flash="Payslip has been paid"
            if len(ids)>1:
                flash="Payslips has been paid"
        return {
            "action":{
                "name":"payslip"
            },
            "flash":flash,
        }

    def get_income_year(self,context={}):
        payslip_id=int(context['refer_id'])

        date_on = context['date_to']
        due_year,due_month,due_day=date_on.split("-")
        due_month=int(due_month)
        due_year_start=due_year+"-01-01"
        due_year_end=due_year+"-12-31"
        due_year = int(due_year)
        period = 12 - due_month

        employee = context['emp_id']
        emp=get_model('hr.employee').browse(employee)

        hire_date=emp.hire_date
        resign_date = emp.resign_date
        if resign_date:
            resign_year,resign_month,resign_day=resign_date.split("-")
            resign_day = int(resign_day)
            resign_year = int(resign_year)
            resign_month = int(resign_month)

        hire_year,hire_month,hire_day=hire_date.split("-")
        hire_month=int(hire_month)
        hire_year=int(hire_year)
        hire_day=int(hire_day)

        if payslip_id == 0:
            income = 0
            income_sum = 0
            income_first = 0
            # employee = context['emp_id']
            # emp_pay=get_model('hr.employee').browse(employee)
            emp_tem =emp.payslip_template_id
            if emp_tem:
                for payitem_line in emp_tem.lines:
                    qty = payitem_line.qty
                    rate = payitem_line.rate
                    if payitem_line.payitem_id.type in ("wage","allow") and payitem_line.payitem_id.fix_income == True:
                        if hire_year == due_year and hire_month == due_month:
                            # if payitem_line.payitem_id.wage_type == "salary":
                            rate_day = rate / 30
                            if hire_day == 1:
                                day = 30
                            elif hire_month == 2:
                                day = 29 - hire_day
                            elif hire_month in (4,6,9,11):
                                day = 31 - hire_day
                            else:
                                day = 32 - hire_day
                            income_first += rate_day * day *qty
                        income_sum += qty * rate
                    elif payitem_line.payitem_id.type=="deduct":
                        if payitem_line.payitem_id.deduct_type in ("thai_social","provident"):
                            continue
                        income_sum-=amt
            else:
                income_sum = emp.salary
                if hire_year == due_year and hire_month == due_month:
                    # if payitem_line.payitem_id.wage_type == "salary":
                    rate_day = emp.salary / 30
                    if hire_day == 1:
                        day = 30
                    elif hire_month == 2:
                        day = 29 - hire_day
                    elif hire_month in (4,6,9,11):
                        day = 31 - hire_day
                    else:
                        day = 32 - hire_day
                    income_first += rate_day * day
            income += ((income_sum or 0) * period) + income_first
            #print("iiiiiiiinnnnnnncomeeeeee2222 ===->",income,income_first,income_sum)
            return income
        else:
            payslip=self.browse(payslip_id)
            employee_id=payslip.employee_id
        to_date=payslip.date_to
        to_year,to_month,to_day=to_date.split("-")
        to_month=int(to_month)
        to_year=int(to_year)
        no_month_to_dec = 12 - to_month

        def cal_inc():
            income=0
            income_sum=0
            income_first = 0
            income_last = 0
            resign_ind = False
            obj2 = self.search_browse([['date_to','=',date_on],['employee_id','=',employee_id.id],['due_date',">=",due_year_start],['due_date','<=',due_year_end]])
            if resign_date:
                if resign_year == due_year and resign_month == due_month:
                    resign_ind = True
            for obj in self.search_browse([['date_to','<=',to_date],['employee_id','=',employee_id.id],['due_date',">=",due_year_start],['due_date','<=',due_year_end]]):
                for line in obj.lines:
                    qty=line.qty or 0
                    rate=line.rate or 0
                    amt=qty*rate
                    item=line.payitem_id
                    if item.type in ("wage","allow"):
                        income+=amt
                    elif item.type=="deduct":
                        if item.deduct_type in ("thai_social","provident","loan"):
                            continue
                        income-=amt
            if no_month_to_dec > 0 and employee_id.work_status == "working":
                emp_pay=get_model('hr.employee').browse(employee_id.id)
                emp_id_pay =emp_pay.payslip_template_id
                if resign_ind == True and obj2:
                    income_sum = 0
                elif emp_id_pay:
                    for payitem_line in emp_id_pay.lines:
                        qty = payitem_line.qty or 0
                        rate = payitem_line.rate or 0
                        amt = qty * rate
                        if payitem_line.payitem_id.type in ("wage","allow"):
                            if hire_year == due_year and hire_month == due_month:
                            # if payitem_line.payitem_id.wage_type == "salary":
                                rate_day = rate / 30
                                if hire_day == 1:
                                    day = 30
                                elif hire_month == 2:
                                    day = 29 - hire_day
                                elif hire_month in (4,6,9,11):
                                    day = 31 - hire_day
                                else:
                                    day = 32 - hire_day
                                income_first += rate_day * day * qty
                            if resign_ind == True:
                                rate_day = rate / 30
                                if resign_month == 2 and resign_day == 28 or resign_day == 29:
                                    day = 30
                                elif resign_day > 30:
                                    day = 30
                                else:
                                    day = resign_day
                                income_last += rate_day * day
                            income_sum += amt
                        elif payitem_line.payitem_id.type=="deduct":
                            if payitem_line.payitem_id.deduct_type in ("thai_social","provident","loan"):
                                continue
                            income_sum-=amt
                else:
                    income_sum = emp_pay.salary
                    if hire_year == due_year and hire_month == due_month:
                    # if payitem_line.payitem_id.wage_type == "salary":
                        rate_day = emp.salary / 30
                        if hire_day == 1:
                                day = 30
                        elif hire_month == 2:
                            day = 29 - hire_day
                        elif hire_month in (4,6,9,11):
                            day = 31 - hire_day
                        else:
                            day = 32 - hire_day
                        income_first += rate_day * day
                if resign_ind == True:
                    income += (income_last or 0)
                else:
                    income += (income_sum or 0) * no_month_to_dec
            print("iiiiiiiinnnnnnncomeeeeee ===->",income,income_sum,resign_ind)
            return income

        if hire_year < to_year:
            income = cal_inc()
        elif hire_year == to_year:
            if hire_month <= to_month:
                income = cal_inc()
        return income

    def get_pit(self,context={}):
        if not context.get('refer_id'):
            return {}

        payslip_id=int(context['refer_id'])
        payslip=self.browse(payslip_id)
        employee=payslip.employee_id
        to_date=payslip.date_to
        context['date_to']=to_date
        context['emp_id']=employee.id
        income = self.get_income_year(context=context)

        context['employee_id']=employee.id
        context['year_income']=income
        context['year_date'] = to_date
        line=get_model("hr.payitem").compute_thai_tax(context=context)
        del line['tax_month']

        vals={}
        vals["B1"]="Contribution to provident fund (The part that exceeds 10,000 Baht)"
        vals["B2"]='Contribution to government pension fund'
        vals["B3"]='Contribution to private school teacher fund'
        vals["B4"]='Taxpayer age over 65 years of age with 190,000 baht income exemption'
        vals["B4a"]=""
        vals["B4b"]=""
        vals["B5"]='Spouse age over 65 years of age with 190,000 baht income exemption'
        vals["B6"]='Severance pay received under the Labor Law(In case taxpayer chooses to include in tax computation)'
        vals["B7"]='Total (1. to 6.) to be filled in A2' 
        vals["C1"]='Taxpayer'
        vals["C2"]="Spouse (30,000 Baht for spouse with income that is combined with taxpayer's income in tax computation or spouse with no income)"
        vals["C3a"]="Child : 15,000 Baht per child"
        vals["C3b"]="Child : 17,000 Baht per child"
        vals["C4a"]="Father of taxpayer"
        vals["C4b"]="Mother of taxpayer"
        vals["C4c"]="Father of Spouse with income that is combined with taxpayer's income in computation or of Spouse with no income"
        vals["C4d"]="Mother of Spouse with income that is combined with taxpayer's income in computation or of Spouse with no income"
        vals["C5"]="Disabled care expense allowance"
        vals["C6"]="Health Insurance Premium for Taxpayer's and Spouse's Parent"
        vals["C7"]="Life Insurance Premium"
        vals["C7a"]=""
        vals["C7b"]=""
        vals["C8"]="Contribution to Provident Fund (The part that dose not exceed 10,000 baht)"
        vals["C9"]="Payment for purchase of shares retirement mutual fund"
        vals["C10"]="Payment for purchase of long-term equity fund"
        vals["C11"]="Interest paid on loans for purchase, hire purchase, or construction of residence building"
        vals["C12"]="Building Purchase cost"
        vals["C13"]="Contribution to social security fund"
        vals["C14"]="Total (1. to 13.) to be filled in A6"
        vals["A1"]="Salary, wage, pension etc. (Plus exempted income from B6)"
        vals["A2"]="Less exempted income (from B7)"
        vals["A3"]="Income after deduction of exempted income (1. - 2.)"
        vals["A4"]="Less expense(40% of 3. but not exceeding legal limit)"
        vals["A5"]="Income after deduction of expense (3. - 4.)"
        vals["A6"]="Less allowances (from C14.)"
        vals["A7"]="Income after deduction of allowances (5. - 6.)"
        vals["A8"]="Less contribution to education (2 times of the contribution paid but not exceeding 10% of 7.)"
        vals["A9"]="Income after deduction of contribution to education (7. - 8.)"
        vals["A10"]="Less donation (not exceed 10% of 9.)"
        vals["A11"]="Net Income (9. - 10.)"
        vals["A12"]="Tax computed from Net Income in 11."
        vals["A13"]="Less Withholding Income Tax"
        vals["A14"]="(Total attached documents for 8. ,10. and 13. .......page(s))"
        vals["A15"]="Plus additional tax payment (from C 6. of continued page (s)(if any))"
        vals["A16"]="Less excess tax payment (from C 7. of continued page (s) (if any))"
        vals["A17"]="Less tax payment from P.N.D.91 (In the case of additional filing)"
        vals["A18"]="Tax additional Payment or Excess Payment"
        vals["A19"]="Plus surcharge (if any)"
        vals["A20"]="Additional tax payable/ overpaid tax"
        vals["A21"]="Add surcharge (if any)"
        vals["A22"]="Total additional tax payable/ overpaid tax"

        # reorder code 
        def key(item):
            key_pat = re.compile(r"(\D+)(\d+)")
            m=key_pat.match(item[0])
            if m:
                return m.group(1), int(m.group(2))
            else:
                return ('',0)
        no=1
        lines=[]
        for k,v in sorted(line.items(),key=key):
            lines.append({
                'no': "%s."%(no),
                'code': k,
                'item': vals.get(k,''),
                'amount': v,
            })
            no+=1
        data={
            'employee':' '.join(s for s in [(employee.title and employee.title+'.' or ''),(employee.first_name or ''),(employee.last_name or '')]),
            'number': payslip.run_id.number,
            'date': payslip.due_date,
            'lines': lines,
        }
        return data

    def onchange_payrun(self,context={}):
        # copy date from/to from payrun to payslip
        data=context["data"]
        payrun_id=int(data.get('run_id'))
        date_from=get_model('hr.payrun').browse(payrun_id).date_from
        date_to=get_model('hr.payrun').browse(payrun_id).date_to
        data['date_from']=date_from
        data['date_to']=date_to
        data['due_date']=date_to
        return data

    def to_draft(self,ids,context):
        if not any(ids):
            return
        for obj in self.browse(ids):
            obj.write({"state":"draft"})
            if obj.move_id:
                obj.move_id.to_draft()
                obj.move_id.delete()
        flash="Payslip has been set to draft"
        if len(ids)>1:
            flash="All Payslips has been set to draft"
        return {
            "action":{
                "name":"payslip",
                "mode": "form",
                "active_id": obj.id,
            },
            "flash":flash,
        }

    def copy(self,ids,context):
        obj=self.browse(ids)[0]
        vals={
            "run_id": obj.run_id.id,
            "employee_id": obj.employee_id.id,
            "date_from": obj.date_from,
            "date_to": obj.date_to,
            "due_date": obj.due_date,
            "state": 'draft',
            'department_id': obj.department_id.id,
            "lines": [],
        }
        for line in obj.lines:
            line_vals={
                "slip_id": line.slip_id.id,
                "payitem_id": line.payitem_id.id,
                "qty": line.qty,
                "rate": line.rate,
                "amount": line.amount,
            }
            vals["lines"].append(("create",line_vals))
        new_id=self.create(vals)
        #new_obj=self.browse(new_id)
        return {
            "next": {
                "name": "payslip",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": "Payslip is copied",
        }

    def post_journal(self,ids,context={}):
        settings=get_model("hr.payroll.settings").browse(1)
        if not settings.intg_acc:
            return
        journal_id=settings.journal_id
        bank_account_id=settings.bank_account_id
        sso_account_id=settings.sso_account_id
        sso_comp_support=settings.sso_comp_support or False
        if not journal_id:
            raise Exception("Not found journal (Setting-> Payroll Settings-> Tab Accounting")
        if not bank_account_id:
            raise Exception("Not found Bank Account (Setting-> Payroll Settings-> Tab Accounting")
        if not sso_account_id:
            raise Exception("Not found SSO Account (Setting-> Payroll Settings-> Tab Accounting")
        company_id=get_active_company()
        company=get_model("company").browse(company_id)
        for obj in self.browse(ids):
            total_debit=0
            total_credit=0
            employee_id=obj.employee_id
            emp_name='%s %s'%(employee_id.first_name, employee_id.last_name)
            move_vals={
                "journal_id": journal_id.id,
                "number": obj.number,
                "date": obj.date,
                "narration": '%s - %s' % (obj.run_id.number, emp_name),
                "related_id": "account.payment,%s"%obj.id,
                "company_id": obj.company_id.id,
            }
            move=obj.move_id
            move_id=move.id
            if move:
                for line in move.lines:
                    line.delete()
            else:
                move_id=get_model('account.move').create(move_vals)
            obj.write({
                'move_id': move_id,
            })
            lines=[]
            for line in obj.lines:
                item=line.payitem_id
                amt=line.amount
                debit=0
                credit=0
                desc='%s - %s %s' % (item.name, employee_id.first_name, employee_id.last_name)
                if item.type in ("wage"):
                    if item.wage_type=='salary':
                        pass
                    debit=amt
                elif item.type in ("deduct"):
                    if item.deduct_type=='thai_social':
                        credit=amt
                        if sso_comp_support:
                            lines.append({
                                'move_id': move_id,
                                'description': '%s - %s'%(item.name,company.name or ""),
                                'account_id': sso_account_id.id,
                                'debit': debit,
                                'credit': credit*2,
                            })
                            total_credit+=credit*2
                        debit=credit
                        credit=0
                    elif item.deduct_type=='provident':
                        credit=amt
                elif item.type in ("tax"):
                    if item.tax_type=='thai':
                        pass
                    credit=amt
                elif item.type in ('allow'):
                    debit=amt
                else:
                    print(item.name, " type ", item.type, " ", amt)
                line={
                    'move_id': move_id,
                    'description': desc,
                    'account_id': item.account_id.id,
                    'debit': debit,
                    'credit': credit,
                }
                if amt:
                    lines.append(line)
                    total_credit+=credit
                    total_debit+=debit
            
            credit,debit=0,0
            if total_credit > total_debit:
                debit=total_credit-total_debit 
            else:
                credit=total_debit-total_credit
            line={
                'move_id': move_id,
                'description': '%s - %s'%(bank_account_id.name, company.name or ""),
                'account_id': bank_account_id.id,
                'debit': debit,
                'credit': credit,
            }
            lines.append(line) 
            move=get_model('account.move').browse(move_id)
            # order by debit, credit
            move.write({
                'lines': [('create',line) for line in sorted(lines,key=lambda x: x['debit'], reverse=True)],
            })

    def get_net_fund(self,ids,context={}):
        amt_fund=0
        for obj in self.browse(ids):
            for line in obj.lines:
                item=line.payitem_id
                if item.type in ["contrib","deduct"]:
                    amt_fund+=line.amount
        return amt_fund 
    
    def delete(self,ids,context={}):
        if not ids:
            return
        db=get_connection()
        ids=[x['id'] for x in db.query("select id from hr_payslip where id in (%s)"%','.join([str(id) for id in ids]))]
        for obj in self.browse(ids):
            if obj.state != 'draft':
                emp_name='%s %s'%(obj.employee_id.first_name,obj.employee_id.last_name)
                raise Exception("Payslip's %s has been %s."%(emp_name,obj.state))
            if obj.move_id:
                obj.move_id.to_draft()
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
                'active_id': obj.move_id.id,
            },
            
        }

    def get_data_page(self,context={}):
        if not context.get('refer_id'):
            return {}
        payslip_id=int(context.get('refer_id'))
        payslip=self.browse(payslip_id)
        employee=payslip.employee_id
        company=payslip.company_id
        title=employee.title or ""
        employee_name="%s. %s %s" % (title.title(),employee.first_name or '',employee.last_name or '')
        employee_address=get_model('hr.employee').get_address([employee.id])
        lines=[]
        income=[]
        deduct=[]
        for line in payslip.lines:
            type=line.payitem_id.type
            if type=='contrib':
                continue
            if type in ('wage','allow'):
                income.append({
                    'income': 1,
                    'item': line.payitem_id.name,
                    'amount': line.amount,
                    'type_wage' : line.payitem_id.wage_type,
                })
            else:
                deduct.append({
                    'income': 0,
                    'item': line.payitem_id.name,
                    'amount': line.amount,
                })

        range_amt=len(income) if len(income) > len(deduct) else len(deduct)
        total_deduct=0
        total_income=0
        deduct_lines=[]
        income_lines=[]

        for i in range(len(income)):
            if income[i]['type_wage'] == "salary":
                item_income = income[0]
                income[0] = income[i]
                income[i] = item_income
        
        for i in range(range_amt):
            line={}
            if i < len(income):
                item=income[i]
                total_income+=item['amount']
                vals={
                      'income_description': item['item'], #depricate
                      'income_amt': item['amount'], #depricate
                      'income_no': i+1, #depricate
                      'no': i+1,
                      'description': item['item'],
                      'amount': item['amount'],
                }
                line.update(vals)
                income_lines.append(vals)
            if i < len(deduct):
                item=deduct[i]
                vals={
                      'deduct_description': item['item'],
                      'deduct_amt':item['amount'],
                      'deduct_no': i+1,
                      'no': i+1,
                      'description': item['item'],
                      'amount': item['amount'],
                }
                line.update(vals)
                deduct_lines.append(vals)
                total_deduct+=item['amount']
            lines.append(line)
        # increase space
        limit=15
        if len(income_lines) < limit:
            for nline in range(len(income_lines),limit):
                income_lines.append({
                    'description': '',
                })
        if len(deduct_lines) < limit:
            for dline in range(len(deduct_lines),limit):
                deduct_lines.append({
                    'description': '',
                })
        ctx={
            'year': context.get("year") or datetime.now().strftime("%Y"),
            'date_from': payslip.date_from,
        }
        ytd=employee.get_ytd(context=ctx)
        def date2thai(date):
            if not date:
                return date
            return utils.date2thai(date,format='%(d)s/%(m)s/%(BY)s')
        data={
            'ref': payslip.run_id.number,
            'employee_name': employee_name,
            'emp_name': employee_name,
            'emp_code': employee.code,
            'emp_position': employee.position,
            'comp_name': company.name,
            'dpt_name': employee.department_id.name,
            'dpt_code': employee.department_id.code,
            'date': date2thai(payslip.date_from),
            'start_date': date2thai(payslip.date_from),
            'end_date': date2thai(payslip.date_to),
            'pay_date': date2thai(payslip.due_date),
            'bank_acc': employee.bank_account,
            'employee_address': employee_address or "Empty Address",
            'amount_net': payslip.amount_net,
            'total_pay': payslip.amount_net,
            'total_deduct': total_deduct,
            'total_income': total_income,
            'lines':lines,
            'deduct_lines':deduct_lines,
            'income_lines':income_lines,
            'year_income': ytd['year_income'],
            'year_tax': ytd['year_tax'],
            'year_soc': ytd['year_soc'],
            'year_prov': ytd['year_prov'],
            'year_acc_prov': ytd['year_acc_prov'],
        }
        comp=get_model('settings').browse(1)
        if comp.logo:
            data['logo']=get_file_path(comp.logo)
        st=get_model("settings").browse(1)
        if st.addresses:
            data['comp_address']=st.addresses[0].address_text
        return data

    def get_data_old(self,ids,context={}):
        settings=get_model("settings").browse(1)
        pages=[]
        for obj in self.browse(ids):
            if not context.get('refer_id'):
                context['refer_id']=obj.id
            context['year']=obj.date_to[:4]
            data=self.get_data_page(context=context)
            pages.append(data)
        if pages:
            pages[-1]["is_last_page"]=True
        return {
            "pages": pages,
            "logo": get_file_path(settings.logo),
        }

    def get_data(self,ids,context={}):
        settings=get_model("settings").browse(1)
        pages=[]
        for obj in self.browse(ids):
            context['refer_id']=obj.id # XXX
            context['year']=obj.date_to[:4]
            data=self.get_data_page(context=context)
            data["logo"]=get_file_path(settings.logo)
            pages.append(data)
        return pages
    
    def to_pay(self,ids,context={}):
        obj=self.browse(ids)[0]
        obj.write({
            'state': 'paid',
        })
        return {
            'next': {
                'name': 'payslip',
                'mode': 'form',
                'active_id': obj.id,
            },
            'flash': 'Payslip %s has been paid'%(obj.employee_id.name_get() or ''),
        }
    
    def onchange_rate(self,context={}):
        data=context['data']
        currency_id=data['currency_id']
        totals={}
        if currency_id:
            currency=get_model('currency').browse(currency_id)
            data['currency_rate']=(currency.sell_rate or 1)
            for line in data['lines']:
                qty=line['qty'] or 0
                rate=line['rate'] or 0
                rate=rate*data['currency_rate']
                line['amount']=qty*rate
                item_id=line.get("payitem_id")
                if not item_id:
                    continue
                item=get_model("hr.payitem").browse(item_id)
                t=item.type
                if t not in totals:
                    totals[t]=0
                totals[t]+=line["amount"]
        data["amount_wage"]=totals.get("wage",0)
        data["amount_allow"]=totals.get("allow",0)
        data["amount_deduct"]=totals.get("deduct",0)
        data["amount_tax"]=totals.get("tax",0)
        data["amount_post_allow"]=totals.get("post_allow",0)
        data["amount_post_deduct"]=totals.get("post_deduct",0)
        data["amount_net"]=data["amount_wage"]+data["amount_allow"]-data["amount_deduct"]-data["amount_tax"]+data["amount_post_allow"]-data["amount_post_deduct"]
        return data
    
    def write(self,ids,vals,**kw):
        self.function_store(ids)
        super().write(ids,vals,**kw)

    def create(self,vals,**kw):
        new_id=super().create(vals,**kw)
        self.function_store([new_id])
        return new_id

PaySlip.register()
