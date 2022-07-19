from netforce.model import Model,fields,get_model
from netforce import database
from netforce import access
from datetime import *
import time
import json
from decimal import *

class Time(Model):
    _name="time.entry"
    _string="Time Entry"
    _audit_log=True
    _fields={
        "date": fields.Date("Date",required=True,search=True),
        "client_id": fields.Many2One("contact","Client",search=True),
        #"jc_job_id": fields.Many2One("jc.job","Related Job",search=True),
        "job_bill_type": fields.Selection([["hour","Hourly"],["flat","Flat Fee"]],"Billing Type",function="_get_related",function_context={"path":"jc_job_id.bill_type"}),
        "user_id": fields.Many2One("base.user","User",required=True),
        "actual_hours": fields.Decimal("Duration",scale=6),
        "bill_hours": fields.Decimal("Billable Hours",scale=6),
        "notes": fields.Text("Remarks",search=True),
        "description": fields.Text("Work Description",search=True,required=True),
        "start_time": fields.Time("Start Time"),
        "end_time": fields.Time("End Time"),
        "timer_start": fields.DateTime("Timer Start"),
        "bill_type": fields.Selection([["hour","Hourly"],["flat","Flat Fee"]],"Billing Type",function="get_bill_type"),
        "rate": fields.Decimal("Hourly Rate"),
        "invoice_id": fields.Many2One("account.invoice","Invoice",search=True),
        "state": fields.Selection([["draft","Draft"],["submitted","Submitted"],["approved","Approved"],["invoiced","Invoiced"],["merged","Merged"]],"Status",search=True,required=True),
        "date_week": fields.Char("Week",function="get_date_agg",function_multi=True),
        "date_month": fields.Char("Month",function="get_date_agg",function_multi=True),
        "flat_fee": fields.Decimal("Amount"),
        "amount": fields.Decimal("Amount",function="get_amount"),
        "own_user": fields.Boolean("Own User",store=False,function_search="search_own_user"),
        "product_id": fields.Many2One("product","Product"),
        "rate_report": fields.Decimal("Hourly Rate",function="get_rate_report"), # XXX: remove this
    }
    _order="date desc,start_time,id desc"

    def _get_hours(self,context={}):
        defaults=context.get("defaults",{})
        date=defaults.get("date")
        start_time=defaults.get("start_time")
        end_time=defaults.get("end_time")
        if date and start_time and end_time:
            t0=datetime.strptime(date+" "+start_time,"%Y-%m-%d %H:%M:%S")
            t1=datetime.strptime(date+" "+end_time,"%Y-%m-%d %H:%M:%S")
            dt=int((t1-t0).total_seconds())/Decimal(3600)
            return dt

    def _get_client(self,context={}):
        defaults=context.get("defaults") or {}
        job_id=defaults.get("jc_job_id")
        if job_id:
            job=get_model("jc.job").browse(job_id)
            return job.contact_id.id

    def _get_product(self,context={}):
        user_id=access.get_active_user()
        user=get_model("base.user").browse(user_id)
        return user.product_id.id

    def _get_rate(self,context={}):
        user_id=access.get_active_user()
        user=get_model("base.user").browse(user_id)
        prod=user.product_id
        if not prod:
            return
        return prod.sale_price

    def _get_bill_type(self,context={}):
        user_id=access.get_active_user()
        user=get_model("base.user").browse(user_id)
        prod=user.product_id
        if prod and prod.uom_id.name=="Hour":
            return "hour"
        return "flat"

    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "user_id": lambda *a: access.get_active_user(),
        "state": "draft",
        "actual_hours": _get_hours,
        "bill_hours": _get_hours,
        "product_id": _get_product,
        "bill_type": _get_bill_type,
        "rate": _get_rate,
        "client_id": _get_client,
    }

    def stop_user_timers(self,context={}):
        user_id=access.get_active_user()
        for obj in self.search_browse([["timer_start","!=",None],["user_id","=",user_id]]):
            obj.stop_timer(context=context)

    def start_timer(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.state!="draft":
            raise Exception("Invalid status")
        t=context.get("client_time")
        if not t:
            raise Exception("Missing client time")
        self.stop_user_timers(context=context)
        obj.write({"timer_start":t})
        start_time=t[11:]
        obj.write({"start_time":start_time})
        return {
            "timer_start": t,
        }

    def start_new_timer(self,context={}):
        obj_id=self.create({})
        obj=self.browse(obj_id)
        obj.start_timer(context=context)
        return obj_id

    def stop_timer(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.state!="draft":
            obj.write({"timer_start":None})
            return
        t=context.get("client_time")
        if not t:
            raise Exception("Missing client time")
        if not obj.timer_start:
            raise Exception("Missing start time")
        d1=datetime.strptime(t,"%Y-%m-%d %H:%M:%S")
        d0=datetime.strptime(obj.timer_start,"%Y-%m-%d %H:%M:%S")
        dt=(d1-d0).seconds
        new_hours=((obj.actual_hours or 0)*3600+dt)/Decimal(3600)
        obj.write({"timer_start":None,"actual_hours":new_hours})
        start_time=t[11:]
        obj.write({"end_time":start_time})
        return {
            "next": {
                "name": "time_popup_stop",
                "active_id": obj.id,
            }
        }

    def onchange_job(self,context={}):
        data=context["data"]
        job_id=data["jc_job_id"]
        job=get_model("jc.job").browse(job_id)
        data["client_id"]=job.contact_id.id
        return data

    def onchange_actual_hours(self,context={}):
        data=context["data"]
        data["bill_hours"]=data["actual_hours"]
        if data["date"] and data["start_time"]:
            t0=datetime.strptime(data["date"]+" "+data["start_time"],"%Y-%m-%d %H:%M:%S")
            t1=t0+timedelta(seconds=round(data["actual_hours"]*3600))
            data["end_time"]=t1.strftime("%H:%M:%S")
        return data

    def onchange_start_time(self,context={}):
        return self.update_actual_hours(context=context)

    def onchange_end_time(self,context={}):
        return self.update_actual_hours(context=context)

    def update_actual_hours(self,context={}):
        data=context["data"]
        date=data["date"]
        start_time=data["start_time"]
        end_time=data["end_time"]
        t0=datetime.strptime(date+" "+start_time,"%Y-%m-%d %H:%M:%S")
        t1=datetime.strptime(date+" "+end_time,"%Y-%m-%d %H:%M:%S")
        dt=int((t1-t0).total_seconds())/Decimal(3600)
        data["actual_hours"]=dt
        data["bill_hours"]=dt
        return data

    def write(self,ids,vals,context={}):
        if "actual_hours" in vals or "bill_hours" in vals:
            for obj in self.browse(ids):
                if obj.state in ("approved","invoiced"):
                    raise Exception("Can't change hours in approved or invoiced time entries")
        super().write(ids,vals,context=context)
        if vals.get("actual_hours") and not vals.get("bill_hours"):
            self.write(ids,{"bill_hours":vals["actual_hours"]},context=context)

    def get_date_agg(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            d=datetime.strptime(obj.date,"%Y-%m-%d")
            month=d.strftime("%Y-%m")
            week=d.strftime("%Y-W%W")
            vals[obj.id]={
                "date_week": week,
                "date_month": month,
            }
        return vals

    def submit(self,ids,context):
        vals={}
        for obj in self.browse(ids):
            job=obj.jc_job_id
            if job.bill_type=="flat":
                raise Exception("Can not submit because flat fee job")
            obj.write({"state":"submitted"})
        return vals

    def approve(self,ids,context):
        vals={}
        for obj in self.browse(ids):
            job=obj.jc_job_id
            if job.bill_type=="flat":
                raise Exception("Can not approve because flat fee job")
            obj.write({"state":"approved"})

    def to_draft(self,ids,context):
        vals={}
        for obj in self.browse(ids):
            obj.write({"state":"draft"})

    def onchange_user(self,context={}):
        data=context["data"]
        user_id=data["user_id"]
        user=get_model("base.user").browse(user_id)
        prod=user.product_id
        data["product_id"]=prod.id
        data["rate"]=prod.sale_price if prod else None
        data=self.onchange_product(context=context)
        return data

    def onchange_product(self,context={}):
        data=context["data"]
        prod_id=data["product_id"]
        if prod_id:
            prod=get_model("product").browse(prod_id)
            if prod.uom_id.name=="Hour":
                data["bill_type"]="hour"
                data["rate"]=prod.sale_price
            else:
                data["bill_type"]="flat"
                data["flat_fee"]=prod.sale_price
                data["rate"]=None
                data["bill_hours"]=None
            data["notes"]=prod.description or ""
        else:
            data["bill_type"]="flat"
        return data

    def copy_to_invoice(self,ids,context):
        contact_id=None
        job_id=None
        total=0
        for obj in self.browse(ids):
            job=obj.jc_job_id
            if not job:
                raise Exception("Missing job for time entry: %s"%obj.description)
            if job.bill_type=="flat":
                raise Exception("Can not invoice because flat fee job")
            if not job.contact_id:
                raise Exception("Missing client for time entry: %s"%obj.description)
            if obj.state!="approved":
                raise Exception("Time entry must be approved before creating invoice.")
            if not contact_id:
                contact_id=job.contact_id.id
            else:
                if contact_id!=job.contact_id.id:
                    raise Exception("Multiple clients")
            if not job_id:
                job_id=obj.jc_job_id.id
            else:
                if job_id!=obj.jc_job_id.id:
                    raise Exception("Multiple jobs")
            total+=obj.amount or 0
        if not job_id:
            raise Exception("Missing job")
        job=get_model("jc.job").browse(job_id)
        prod=job.product_id
        if not prod:
            raise Exception("Missing product in job %s"%job.number)
        vals={
            "type": "out",
            "inv_type": "invoice",
            "contact_id": contact_id,
            "related_id": "jc.job,%s"%job_id,
            "ref": job.number,
            "lines": [("create",{
                "product_id": prod.id,
                "description": prod.description or prod.name or "/",
                "qty": 1,
                "uom_id": prod.uom_id.id,
                "unit_price": total,
                "amount": total,
                "account_id": prod.sale_account_id.id,
                "tax_id": prod.sale_tax_id.id,
            })],
        }
        inv_id=get_model("account.invoice").create(vals,context={"type":"out","inv_type":"invoice"})
        inv=get_model("account.invoice").browse(inv_id)
        for obj in self.browse(ids):
            obj.write({"invoice_id":inv_id,"state":"invoiced"})
        return {
            "alert": "Invoice %s created"%inv.number,
            "alert_type": "success",
        }

    def get_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.bill_type=="flat":
                amt=obj.flat_fee
            else:
                amt=round((obj.bill_hours or 0)*(obj.rate or 0),2)
            vals[obj.id]=amt
        return vals

    def merge(self,ids,context={}):
        if len(ids)<2:
            raise Exception("Select at least 2 time entries")
        obj=self.browse(ids[0])
        date=obj.date
        job_id=obj.jc_job_id.id
        max_rate=None
        for obj in self.browse(ids):
            if obj.state=="merged":
                raise Exception("Invalid status")
            if obj.date!=date:
                raise Exception("Different dates")
            if obj.jc_job_id.id!=job_id:
                raise Exception("Different jobs")
            if not obj.rate:
                raise Exception("Missing rate for time entry: %s"%obj.description)
            if not max_rate or obj.rate>max_rate:
                max_rate=obj.rate
                max_time=obj
        for obj in self.browse(ids):
            if obj.id!=max_time.id:
                obj.write({"state":"merged"})
        notes=max_time.notes or ""
        if notes:
            notes+=" | "
        notes+="Additional lawyer(s) not charged: "+", ".join([o.user_id.code or o.user_id.login for o in self.browse(ids) if o.id!=max_time.id])
        max_time.write({"notes":notes})

    def send_notifs(self,days=14,min_hours=8,user_codes=["RM"],context={}):
        d_from=datetime.today()-timedelta(days=days)
        d_to=datetime.today()
        cond=[["date",">=",d_from.strftime("%Y-%m-%d")],["date","<=",d_to.strftime("%Y-%m-%d")]]
        hours={}
        for obj in self.search_browse(cond):
            k=(obj.user_id.id,obj.date)
            hours.setdefault(k,0)
            hours[k]+=obj.actual_hours or 0
        for code in user_codes:
            res=get_model("base.user").search([["code","=",code]])
            if not res:
                raise Exception("Invalid user code: %s"%code)
            user_id=res[0]
            user=get_model("base.user").browse(user_id)
            lines=[]
            d=d_from
            while d<d_to:
                if d.weekday() in (5,6):
                    d+=timedelta(days=1)
                    continue
                res=get_model("hr.holiday").search([["date","=",d.strftime("%Y-%m-%d")]])
                if res:
                    d+=timedelta(days=1)
                    continue
                k=(user_id,d.strftime("%Y-%m-%d"))
                h=hours.get(k,0)
                if h<min_hours:
                    line="Insufficient recorded time on %s: %s hours"%(d.strftime("%Y-%m-%d"),h)
                    lines.append(line)
                d+=timedelta(days=1)
            if lines:
                res=get_model("email.template").search([["name","=","time_notif"]])
                if not res:
                    raise Exception("Email template not found")
                tmpl_id=res[0]
                msg="<br/>".join(lines)
                if not user.email:
                    raise Exception("Missing email for user %s"%user.login)
                data={
                    "user": user,
                    "message": msg,
                }
                get_model("email.template").create_email([tmpl_id],data)
        get_model("email.message").send_emails_async()

    def search_own_user(self,clause,context={}):
        user_id=access.get_active_user()
        return ["user_id","=",user_id]

    def get_bill_type(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            prod=obj.product_id
            if prod and prod.uom_id.name=="Hour":
                bill_type="hour"
            else:
                bill_type="flat"
            vals[obj.id]=bill_type
        return vals

    def get_rate_report(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            rate=None
            if obj.bill_type=="hour":
                if obj.rate:
                    rate=obj.rate
                elif obj.user_id.product_id:
                    rate=obj.user_id.product_id.sale_price
            vals[obj.id]=rate
        return vals

    def copy(self,ids,context={}):
        for obj in self.browse(ids):
            res=obj._copy(vals={"description":(obj.description or "")+" (Copy)"})
            new_id=res[0]
        return {
            "alert": "Time entry duplicated.",
            "next": {
                "name": "jc_time_entry",
                "mode": "form",
                "active_id": new_id,
            },
        }

Time.register()
