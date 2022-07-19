import time

from netforce.model import Model, fields, get_model
from netforce import database

class Notification(Model):
    _name="hr.notification"
    _fields={
        "subject": fields.Char("Title",required=True),
        "description": fields.Text("Description"),
        'birthday_ntf': fields.Boolean("Birthday Notify"),
    }

    def birthday_notify(self,context={}):
        db=database.get_connection()
        cr_time=time.strftime("%Y-%m-%d %H:%M:%S")
        cr_yyyy=cr_time[0:4]
        cr_mm=cr_time[5:7]
        cr_dd=cr_time[8:10]
        today="%s%s"%(cr_dd,cr_mm)
        print(cr_time, " checking birthday")
        subject="Happy Birth Day"
        body=subject
        ntf=get_model("hr.notification").browse(1)
        if ntf:
            subject=ntf.subject
            body=ntf.description
        count=0
        for emp in get_model("hr.employee").search_browse([['work_status','=','working']]):
            if emp.birth_date:
                mm=emp.birth_date[5:7]
                dd=emp.birth_date[8:10]
                emp_date="%s%s"%(dd,mm)
                if emp_date==today:
                    user_id=emp.user_id.id
                    sql="select id from message where related_id='hr.employee,%s' and extract(year from create_time) = %s"
                    res=db.query(sql, emp.id, cr_yyyy)
                    if not res:
                        if emp.email:
                            self.trigger([emp.id],"birthday_notify")
                            print("happby birthday %s %s"%(emp.first_name,emp.last_name))
                        if user_id:
                            vals={
                                'subject': subject,
                                'to_id': user_id,
                                'body': body,
                                "related_id": "hr.employee,%s"%emp.id,
                            }
                            msg_id=get_model("message").create(vals)
                            print("created message #", msg_id)
                        count+=1
        print("SEND TOTOAL: #",count)

Notification.register()
