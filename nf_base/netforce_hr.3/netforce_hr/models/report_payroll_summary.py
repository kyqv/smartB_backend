import time
from calendar import monthrange

from netforce.model import Model,fields,get_model
from netforce.access import get_active_company

class ReportCycleItem(Model):
    _name="report.payroll.summary"
    _string="Report Payroll Summary"
    _transient=True

    _fields={
        "date": fields.Date("Month"),
        "date_from": fields.Date("From", required=True),
        "date_to": fields.Date("To", required=True),
        'emp_type': fields.Selection([
            ['monthly','Monthly'],
            ['daily','Daily'],
            ['hourly','Job'],
        ],'Employee Type'),
    }

    def default_get(self,field_names=None,context={},**kw):
        defaults=context.get("defaults",{})
        date=defaults.get('date',time.strftime("%Y-%m-%d"))
        year,month=time.strftime("%Y-%m").split("-")
        weekday, total_day=monthrange(int(year), int(month))
        date_from=defaults.get('date_from','%s-%s-01'%(year,month))
        date_to=defaults.get('date_to','%s-%s-%s'%(year,month,total_day))
        res={
            'date': date,
            'date_from': date_from,
            'date_to': date_to,
            'emp_type': 'monthly',
        }
        print('report.payroll.summary', res)
        return res
    
    def get_report_data(self,ids=None,context={}):
        defaults=self.default_get(context=context)
        comp_id=get_active_company()
        comp=get_model('company').browse(comp_id)
        emp_type=defaults.get('emp_type','monthly')
        date_to=defaults.get('date_to')
        date_from=defaults.get('date_from')
        types={
            'monthly':'Monthly',
            'daily': 'Daily',
            'hourly': 'Job',
        }
        if ids:
            obj=self.browse(ids)[0]
            emp_type=obj.emp_type
            date_from=obj.date_from
            date_to=obj.date_to
        lines=[]
        dom=[
            ['date_from','>=',date_from],
            ['date_to','<=',date_to],
        ]
        for payslip in get_model('hr.payslip').search_browse(dom):
            emp=payslip.employee_id
            dpt=emp.department_id
            vals={
                'emp_code': emp.code,
                'emp_id': emp.id,
                'emp_name': '%s %s'%(emp.first_name or '', emp.last_name or''),
                'dpt_code': dpt.code,
                'dpt_name': dpt.name,
                'postion': emp.position or '',
                #line
                'salary': 0,
                'bonus': 0,
                'other_income': 0,
                'ot': 0,
                'total_income': 0,
                'other_expense': 0,
                'soc': 0,
                'prov': 0,
                'loan': 0,
                'tax': 0,
                'total_expense': 0,
                'net_income': payslip.amount_net or 0,
            }
            for line in payslip.lines:
                item=line.payitem_id
                amount=line.amount or 0
                if item.type in ('wage','allow'):
                    if item.wage_type=='salary':
                        vals['salary']+=amount
                    elif item.wage_type=='overtime':
                        vals['ot']+=amount
                    elif item.wage_type=='bonus':
                        vals['bonus']+=amount
                    elif item.wage_type=='commission':
                        vals['other_income']+=amount
                    else:
                        vals['other_income']+=amount
                    vals['total_income']+=amount
                elif item.type=='deduct':
                    if item.deduct_type=='thai_social':
                        vals['soc']+=amount
                    elif item.deduct_type=='loan':
                        vals['loan']+=amount
                    elif item.deduct_type=='provident':
                        vals['prov']+=amount
                    else:
                        vals['other_expense']+=amount
                    vals['total_expense']+=amount
                elif item.type=='tax':
                    vals['tax']+=amount
                    vals['total_expense'] += vals['tax']

            lines.append(vals)
        dpts={}
        for line in lines:
            dpt_code=line['dpt_code']
            if line['dpt_code'] not in dpts.keys():
                dpts[dpt_code]=[line]
            else:
                dpts[dpt_code].append(line)

        nlines=[]
        gline={
                'dpt_name': '',
                'salary': 0,
                'bonus': 0,
                'total_income': 0,
                'other_income': 0,
                'ot': 0,
                'income': 0,
                'other_expense': 0,
                'soc': 0,
                'prov': 0,
                'loan': 0,
                'tax': 0,
                'total_expense': 0,
                'net_income': 0,
                'last': True,
        }
        ssline=gline.copy()
        for dpt_code, lines in sorted(dpts.items(),key=lambda x: x[0] or ''):
            sline=ssline.copy()
            sline['is_total']=True
            no=1
            for line in sorted(lines, key=lambda x: x['emp_code']):
                line['no']=no
                if no > 1:
                    line['dpt_code']=''
                for lkey in line.keys():
                    if lkey in sline.keys():
                        if lkey=='dpt_name':
                            sline[lkey]=line[lkey]
                        else:
                            sline[lkey]+=line[lkey] or 0
                            gline[lkey]+=line[lkey]  or 0
                nlines.append(line)
                no+=1
            nlines.append(sline)
        gline['is_grand']=True
        nlines.append(gline)
        data={
            'comp_name': comp.name or'',
            'emp_type': types[emp_type],
            'lines': nlines,
            'report_date': date_to,
        }
        return data

    def onchange_date(self,context={}):
        data=context['data']
        date=data['date']
        year,month,day=date.split("-")
        weekday, total_day=monthrange(int(year), int(month))
        data['date_from']="%s-%s-01"%(year,month)
        data['date_to']="%s-%s-%s"%(year,month,total_day)
        return data

ReportCycleItem.register()
