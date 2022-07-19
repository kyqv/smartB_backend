from datetime import datetime, timedelta

from netforce.model import Model, fields

class ScheduleLine(Model):
    _name="hr.schedule.line"
    _string="Schedule Line"
    
    def get_time_stop(self,ids,context={}):
        res={}
        for obj in self.browse(ids):
            datenow=datetime.now().strftime("%Y-%m-%d")
            time_start='%s %s'%(datenow,obj.time_start)
            time_total=obj.time_total or 0
            if obj.skip_mid:
                time_total+=1 #12.00-13.00
            seconds=(time_total)*60*60
            time_stop=datetime.strptime(time_start,'%Y-%m-%d %H:%S')+timedelta(seconds=seconds)
            res[obj.id]=time_stop.strftime("%H:%S")
        return res

    _fields={
        'schedule_id': fields.Many2One("hr.schedule","Schedule"),
        "dow": fields.Selection([["1","Monday"],["2","Tuesday"],["3","Wednesday"],["4","Thursday"],["5","Friday"],["6","Saturday"],["7","Sunday"]],"Day Of Week"),
        'time_start': fields.Char("Time Start"),
        'time_stop': fields.Char("Time Stop"),
    }
    
    order="dow, time_start"

ScheduleLine.register()
