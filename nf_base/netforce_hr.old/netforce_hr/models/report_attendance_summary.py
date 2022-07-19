import time
from calendar import monthrange
from datetime import datetime, timedelta

from netforce.model import Model,fields,get_model
from netforce.access import get_active_company

from operator import itemgetter

class ReportAttendanceSummary(Model):

    _name="report.attendance.summary"
    _string="Report Attendance Summary"
    _transient=True

    _fields={
        "date_from": fields.Date("From", required=True),
        "date_to": fields.Date("To", required=True),
    }

    def default_get(self,field_names=None,context={},**kw):
        defaults=context.get("defaults",{})
        date=defaults.get('date',time.strftime("%Y-%m-%d"))
        year,month=time.strftime("%Y-%m").split("-")

        weekday, total_day=monthrange(int(year), int(month))
        date_from=defaults.get('date_from','%s-%s-01'%(year,month))
        date_to=defaults.get('date_to','%s-%s-%s'%(year,month,total_day))

        res={
            'date_from': date_from,
            'date_to': date_to,
        }
        return res

    def get_report_data(self,ids,context={}):
        print('report_attendance_summary',ids,context)

        company_id=get_active_company()
        comp=get_model("company").browse(company_id)
        if ids:
            params=self.read(ids,load_m2o=False)[0]
        else:
            params=self.default_get(load_m2o=False,context=context)

        date_from=params.get("date_from")
        date_to=params.get("date_to")

        data={
            'company_name':comp.name,
            'date_from' : date_from,
            'date_to' : date_to,
            'lines':[]
        }
        att_obj = get_model("hr.attendance")

        res=att_obj.search_read([
            ["time",">=",date_from+" 00:00:00"],
            ["time","<=",date_to+" 23:59:59"],
        ],['employee_id','time','action','mode'],order="employee_id,time")

        groups={}
        # employee
        #   date
        #       in_time : out_time
        for r in res:

            dt = r['time']

            dt = datetime.strptime(r['time'],"%Y-%m-%d %H:%M:%S")

            d =  dt.strftime('%Y-%m-%d')
            t =  dt.strftime('%H:%M')

            key = (r['employee_id'][1],d,r['employee_id'][0])

            groups.setdefault(key,[]).append(t)

        lines=[]
        for key,val in groups.items():
            vals={
                'name':key[0],
                'date': key[1],
                'employee_id': key[2],
                'd': key[1], # need in context for link

                }
            if len(val)==1:
                vals['in_time'] = val[0]
                vals['out_time'] = ''

            elif len(val)>1:
                vals['in_time'] = val[0]
                vals['out_time'] = val[-1]
                t2 = datetime.strptime(val[-1],'%H:%M')
                t1 = datetime.strptime(val[0],'%H:%M')

                break_time=1.0 # 1 hr break
                total_time = (t2-t1).seconds/3600.0

                if val[-1] > '11:30': #TODO: this can config
                    total_time -= break_time

                vals['total_time'] = round(total_time,2)

            else:
                continue
            lines.append(vals)

        get = itemgetter('date','name')
        lines.sort(key=get)

        date=False
        for l in lines:
            if l['date']!=date:
                date = l['date']
            else:
                l['date']=''


        data['lines'] = lines

        return data

    def onchange_date(self,context={}):
        data=context['data']
        date=data['date']
        year,month,day=date.split("-")
        weekday, total_day=monthrange(int(year), int(month))
        data['date_from']="%s-%s-01"%(year,month)
        data['date_to']="%s-%s-%s"%(year,month,total_day)
        return data

ReportAttendanceSummary.register()
