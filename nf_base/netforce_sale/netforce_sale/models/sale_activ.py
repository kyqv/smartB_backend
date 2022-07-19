from netforce.model import Model, fields, get_model
from netforce.utils import get_data_path
import time
import smtplib
import poplib
import email
from email.utils import parseaddr, parsedate
from email.header import decode_header
from netforce import database
import datetime
from netforce import access


class Activ(Model):
    _name = "sale.activ"
    _string = "Activity"
    _name_field = "subject"
    _fields = {
        "type": fields.Selection([["meeting", "Meeting"],["call", "Call"],["event", "Event"],["task", "Task"]], "Activity Type", required=True, search=True),
        "user_id": fields.Many2One("base.user", "Assigned To", search=True, required=True),
        "subject": fields.Char("Subject", required=True, size=128, search=True),
        "date": fields.Date("Date", search=True, required=True),
        "due_date": fields.Date("Due Date"),
        "description": fields.Text("Description"),
        "body": fields.Text("Body"),
        "state": fields.Selection([["new", "Not Started"], ["in_progress", "In Progress"], ["done", "Completed"], ["waiting", "Waiting on someone else"], ["deferred", "Deferred"]], "Status", required=True),
        "priority": fields.Selection([["high", "High"], ["normal", "Normal"], ["low", "Low"]], "Priority"),
        "phone": fields.Char("Phone"),
        "email": fields.Char("Email"),
        "start_time": fields.Time("Start Time"),
        "end_time": fields.Time("End Time"),
        "location": fields.Char("Location"),
        "related_id": fields.Reference([["sale.opportunity", "Opportunity"],["sale.quot", "Quotation"],["sale.order", "Sales Order"]], "Related To"),
        "contact_id": fields.Many2One("contact","Contact"),
        "notes": fields.Text("Notes"),
        "send_reminder": fields.Boolean("Send Reminder"),
        "other_users": fields.Many2Many("base.user","Other Involved Users"),
        "notifs": fields.One2Many("notif","related_id","Notifications"),
    }

    def _get_contact(self,context={}):
        defaults=context.get("defaults") or {}
        related_id=defaults.get("related_id")
        if related_id:
            res=related_id.split(",")
            model=res[0]
            record_id=int(res[1])
            rel=get_model(model).browse(record_id)
            if not rel.contact_id:
                return
            return rel.contact_id.id 

    _defaults = {
        "state": "new",
        "date": lambda *a: time.strftime("%Y-%m-%d"),
        "user_id": lambda *a: access.get_active_user(),
        "contact_id": _get_contact,
    }
    _order = "date desc,id desc"

    def create(self,vals,context={}):
        new_id=super().create(vals,context=context)
        self.update_reminders([new_id])
        return new_id

    def write(self,ids,vals,context={}):
        super().write(ids,vals,context=context)
        self.update_reminders(ids)

    def update_reminders(self,ids,context={}):
        for obj in self.browse(ids):
            obj.notifs.delete()
            if not obj.send_reminder:
                continue
            user_ids=[obj.user_id.id]
            user_ids+=[u.id for u in obj.other_users]
            for notif_user_id in user_ids:
                t=obj.date+" 06:00:00"
                title="Reminder: %s"%obj.subject
                vals={
                    "time": t,
                    "title": title,
                    "user_id": notif_user_id,
                    "related_id": "sale.activ,%s"%obj.id,
                }
                get_model("notif").create(vals)

Activ.register()
