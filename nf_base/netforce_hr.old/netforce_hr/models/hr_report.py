from netforce.model import Model, fields, get_model
from netforce import database
import datetime

class Report(Model):
    _name="hr.report"
    _store=False

    def get_attend_hist(self,context={}):
        db=database.get_connection()
        date_from=datetime.date.today()-datetime.timedelta(days=30)
        res=db.query("SELECT user_id,action,time FROM hr_attendance WHERE time>=%s ORDER BY time",date_from)
        days={}
        sign_ins={}
        for r in res:
            if r.action=="sign_in":
                sign_ins[r.user_id]=r.time
            elif r.action=="sign_out":
                last_in=sign_ins.get(r.user_id)
                if not last_in:
                    continue
                day=r.time[:10]
                if last_in[:10]!=day:
                    continue
                t=days.get(day,0)
                t+=(datetime.datetime.strptime(r.time,"%Y-%m-%d %H:%M:%S")-datetime.datetime.strptime(last_in,"%Y-%m-%d %H:%M:%S")).seconds/3600.0
                days[day]=t
        vals=sorted(days.items())
        return {
            "value": vals,
        }

Report.register()
