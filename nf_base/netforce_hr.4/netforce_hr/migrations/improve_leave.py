from netforce.model import get_model
from netforce import migration
from netforce.access import set_active_user, get_active_user, set_active_company, get_active_company

class Migration(migration.Migration):
    _name="improve.leave"
    _version="2.12.0"

    def migrate(self):
        company_id=get_active_company()
        user_id=get_active_user()
        set_active_user(1)
        set_active_company(1)
        rql=('.',',',':')
        def fmt_time(time_txt=""):
            if not time_txt:
                return ""
            time_txt=''.join([t for t in time_txt if t.isdigit() or t in rql])
            count=0
            for t in time_txt:
                if t in rql:
                    count+=1
            if not count and len(time_txt)>=4:
                time_txt=':'.join([time_txt[0:2],time_txt[2:4]])
            elif len(time_txt)>=6:
                h, m='',''
                c=0
                for t in time_txt:
                    if t in rql:
                        m=time_txt[c+1:c+2]
                        break
                    else:
                        h+=t
                    c+=1
                time_txt=':'.join([h.zfill(2),m.zfill(2)])
            time_txt=time_txt.replace(".",":")
            time_txt=time_txt.replace(",",":")
            return time_txt

        for leave in get_model("hr.leave").search_browse([]):
            time_from=fmt_time(leave.time_from)
            time_to=fmt_time(leave.time_to)
            if time_from and time_to:
                leave.write({
                    'start_date': '%s %s:00'%(leave.start_date[0:10],time_from),
                    'end_date': '%s %s:00'%(leave.end_date[0:10],time_to),
                })
        set_active_user(user_id)
        set_active_company(company_id)
    

Migration.register()

