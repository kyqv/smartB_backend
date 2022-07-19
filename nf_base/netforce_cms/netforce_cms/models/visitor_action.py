from netforce.model import Model, fields, get_model
from netforce import database
from netforce import access
from datetime import *
import time

class Action(Model):
    _name = "visitor.action"
    _string = "Action"
    _fields = {
        "time": fields.DateTime("Time",required=True,search=True),
        "visitor_id": fields.Many2One("visitor","Visitor",required=True,search=True),
        "session_id": fields.Many2One("visitor.session","Session",required=True,search=True),
        "action_type": fields.Char("Action Type",required=True,search=True),
        "details": fields.Text("Details",search=True),
        "ip_addr": fields.Char("IP Address",search=True),
        "referrer": fields.Char("Referrer",search=True),
        "location": fields.Char("Location",search=True),
    }
    _order="id desc"

    def upload_action(self,vals,context={}):
        visitor_id_no=vals.get("visitor_id")
        if not visitor_id_no:
            raise Exception("Missing visitor ID")
        session_id_no=vals.get("session_id")
        if not session_id_no:
            raise Exception("Missing session ID")
        action_type=vals.get("action_type")
        if not action_type:
            raise Exception("Missing action type")
        details=vals.get("details")
        user_agent=vals.get("user_agent")
        location=vals.get("location")
        referrer=vals.get("referrer")
        ip_addr=access.get_ip_addr()
        db=database.get_connection()
        res=db.get("SELECT id FROM visitor WHERE id_no=%s",visitor_id_no)
        if res:
            visitor_id=res.id
        else:
            create_time=time.strftime("%Y-%m-%d %H:%M:%S")
            res=db.get("INSERT INTO visitor (id_no,create_time,user_agent) VALUES (%s,%s,%s) RETURNING id",visitor_id_no,create_time,user_agent)
            visitor_id=res.id
        res=db.get("SELECT id FROM visitor_session WHERE id_no=%s",session_id_no)
        if res:
            session_id=res.id
        else:
            create_time=time.strftime("%Y-%m-%d %H:%M:%S")
            res=db.get("INSERT INTO visitor_session (id_no,visitor_id,create_time) VALUES (%s,%s,%s) RETURNING id",session_id_no,visitor_id,create_time)
            session_id=res.id
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        db.execute("INSERT INTO visitor_action (time,visitor_id,session_id,action_type,details,ip_addr,location,referrer) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",t,visitor_id,session_id,action_type,details,ip_addr,location,referrer)

    def get_visitors_per_day(self,context={}):
        db=database.get_connection()
        res=db.query("select date_trunc('day',time) as date,count(distinct visitor_id) as num_visitors from visitor_action group by date order by date")
        data=[]
        for r in res:
            d=datetime.strptime(r.date[:10],"%Y-%m-%d")
            data.append([time.mktime(d.timetuple()) * 1000, r.num_visitors])
        return data

Action.register()
