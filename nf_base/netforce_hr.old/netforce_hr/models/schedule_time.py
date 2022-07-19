from datetime import datetime, timedelta

from netforce.model import Model, fields

class Schedule(Model):
    _name="hr.schedule.time"
    _string="Schedule Time"
    
    def fmt_time(self,time_str):
        time_str=time_str or ""
        time_str=time_str.replace(".",":")
        if not time_str:
            time_str='00:00'
        return  time_str

    def get_total(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            time_start=datetime.strptime(self.fmt_time(obj.time_start),'%H:%S')
            time_stop=datetime.strptime(self.fmt_time(obj.time_stop),'%H:%S')
            hrs=(time_stop-time_start).seconds/60/60
            res[obj.id]=hrs
        return res

    _fields={
        'schedule_id': fields.Many2One('hr.schedule',"Schedule"),
        "name": fields.Char("Name", search=True),
        'time_start': fields.Char("Time Start", size=5),
        'time_stop': fields.Char("Time Stop", size=5),
        'time_total': fields.Decimal("Working Time (HRS)",function="get_total"),
    }


Schedule.register()
