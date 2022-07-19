from datetime import datetime, timedelta

from netforce.model import Model, fields, get_model

FMT_DAY='%Y-%m-%d'
FMT_TIME='%Y-%m-%d %H:%M:%S'
TIME='%H:%M'

class Schedule(Model):
    _name="hr.schedule"
    _string="Work Schedule"
    
    def get_all(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            working_hrs=0
            part1=0
            for time in obj.working_times:
                working_hrs+=(time.time_total or 0)
            time_start=None
            time_stop=time_start
            total=0
            count=len(obj.working_times)-1
            i=0
            for line in obj.working_times:
                if i==0:
                    time_start=(line.time_start or "").replace(".",":")
                    part1=line.time_total or 0
                if i==count:
                    time_stop=(line.time_stop or "").replace(".",":")
                i+=1
            if time_start and time_stop:
                time_start=datetime.strptime(time_start,TIME)
                time_stop=datetime.strptime(time_stop,TIME)
                total=(time_stop-time_start).seconds/60/60
            total_break=total-working_hrs
            res[obj.id]={
                'working_hour': working_hrs,
                'part1': part1,
                'total_break': total_break,
                'working_day': '{%s}'%','.join([
                    (obj.mon and "'mon': (0,1)" or "'mon': (0,0)"),
                    (obj.tue and "'tue': (1,1)" or "'tue': (1,0)"),
                    (obj.wed and "'wed': (2,1)" or "'wed': (2,0)"),
                    (obj.thu and "'thu': (3,1)" or "'thu': (3,0)"),
                    (obj.fri and "'fri': (4,1)" or "'fri': (4,0)"),
                    (obj.sat and "'sat': (5,1)" or "'sat': (5,0)"),
                    (obj.sun and "'sun': (6,1)" or "'sun': (6,0)"),
                    ]),
            }
        return res

    _fields={
        "name": fields.Char("Name", required=True, search=True),
        'working_hour': fields.Decimal("Working Hour/Day", function="get_all",function_multi=True),
        'working_day': fields.Char("Day Status", function="get_all",function_multi=True),
        'total_break': fields.Char("Day Status", function="get_all",function_multi=True),
        'part1': fields.Char("Part1", function="get_all",function_multi=True),
        'working_times': fields.One2Many("hr.schedule.time","schedule_id","Times"),
        'mon': fields.Boolean("Monday"),
        'tue': fields.Boolean("Tuesday"),
        'wed': fields.Boolean("Wednesday"),
        'thu': fields.Boolean("Thursday"),
        'fri': fields.Boolean("Friday"),
        'sat': fields.Boolean("Saturday"),
        'sun': fields.Boolean("Sunday"),
        'lines': fields.One2Many("hr.schedule.line","schedule_id","Lines"),
        "employees":fields.One2Many("hr.employee","schedule_id","Employees")
    }

    _defaults={
        'mon': True,
        'tue': True,
        'wed': True,
        'thu': True,
        'fri': True,
    }
    
    def gen_dow(self,ids,context={}):
        vals={
            'lines':[]
        }
        obj=self.browse(ids)[0]
        for line in obj.lines:
            line.delete()
        dow=[
            (1,obj.mon),
            (2,obj.tue),
            (3,obj.wed),
            (4,obj.thu),
            (5,obj.fri),
            (6,obj.sat),
            (7,obj.sun),
        ]
        days=[x[0] for x in dow if x[1]]
        for day in days:
            for time in obj.working_times:
                vals['lines'].append(('create',{
                    'dow': day,
                    'time_start': time.time_start,
                    'time_stop': time.time_stop,
                }))
        obj.write(vals)
        return {
            'next':
                {
                    'name': 'hr_schedule',
                    'mode': 'form',
                    'active_id': obj.id,
                },
                'flash': 'Generate day of week successfully',
        }
        

    def get_dow(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            dow=set()
            for line in obj.lines:
                dow.update({int(line.dow)-1})
            res[obj.id]=[]
            for r in range(7):
                if r not in list(dow):
                    res[obj.id].append(r)
        return res

    def get_working_time_duration(self, ids, context={}):
        duration = 0
        obj = self.browse(ids)[0]
        start_date = context.get("start_date")
        end_date = context.get("end_date")
        ex_holiday = context.get("ex_holiday")
        if not start_date or not end_date:
            return 0
        holidays = []
        if ex_holiday:
            holidays = get_model("hr.holiday").search_read([],["date"])
            if holidays:
                holidays = [ day["date"] for day in holidays ]
        current_time = datetime.strptime(start_date, FMT_TIME)
        end_time = datetime.strptime(end_date, FMT_TIME)
        while current_time < end_time:
            dow = current_time.weekday()
            for line in obj.lines:
                if int(line.dow) != dow + 1:
                    continue
                if current_time.strftime("%Y-%m-%d") in holidays:
                    continue
                t0 = None
                t1 = None
                wt0 = current_time.replace(hour=int(line.time_start.split(":")[0]), minute=int(line.time_start.split(":")[1]), second=00)
                wt1 = current_time.replace(hour=int(line.time_stop.split(":")[0]), minute=int(line.time_stop.split(":")[1]), second=00)

                if wt1 < current_time or wt0 > end_time:
                    continue
                if current_time < wt0:
                    t0 = wt0
                else:
                    t0 = current_time
                if end_time > wt1:
                    t1 = wt1
                else:
                    t1 = end_time
                if t1 > end_time:
                    t1 = end_time
                duration += (t1 - t0).total_seconds()
            current_time = current_time.replace(hour=00, minute=00, second=00)
            current_time += timedelta(days=1)
        return duration

Schedule.register()
