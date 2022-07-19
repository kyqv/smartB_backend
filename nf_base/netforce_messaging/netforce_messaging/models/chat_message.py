from netforce.model import Model,fields,get_model
from netforce import database
from netforce import access
from netforce import ipc
import json
from datetime import *
import time

class ChatMessage(Model):
    _name="chat.message"
    _string="Chat Message"
    _audit_log=True
    _fields={
        "time": fields.DateTime("Time",required=True,search=True),
        "channel_id": fields.Many2One("chat.channel","Channel",required=True),
        "message": fields.Text("Message",search=True,required=True),
        "user_id": fields.Many2One("base.user","Created By"),
        "to_user_id": fields.Many2One("base.user","Sent To"),
        "read_user_ids": fields.Array("Read By"),
    }
    _defaults={
        "time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": lambda *a: access.get_active_user(),
    }
    _order="time,id"

    def create(self,vals,**kw):
        new_id=super().create(vals,**kw)
        obj=self.browse(new_id)
        obj.channel_id.write({"last_message_time":obj.time})
        return new_id

    def send_message(self,channel_id,msg,to_user_id=None,context={}):
        if not msg:
            raise Exception("Missing message")
        user_id=access.get_active_user()
        if not user_id:
            raise Exception("Missing user")
        user=get_model("base.user").browse(user_id)
        vals={
            "channel_id": channel_id,
            "message": msg,
            "to_user_id": to_user_id,
        }
        msg_id=self.create(vals)
        ipc.send_signal("new_event")
        access.set_active_user(1)
        chan=get_model("chat.channel").browse(channel_id)
        for member in chan.members:
            if member.id==user_id:
                continue
            for dev in member.device_tokens:
                vals={
                    "device_id": dev.id,
                    "title": "%s (%s)"%(user.first_name,chan.name),
                    "message": msg[:140],
                    "state": "to_send",
                }
                get_model("push.notif").create(vals)
        get_model("push.notif").send_notifs_async()
        return {
            "message_id": msg_id,
        }

    def read(self,ids,*args,context={},**kw):
        if not ids:
            return []
        db=database.get_connection()
        res=super().read(ids,*args,context=context,**kw)
        if not context.get("no_mark_read"):
            user_id=access.get_active_user()
            if user_id:
                db.execute("UPDATE chat_message SET read_user_ids=array_append(read_user_ids,%s) WHERE id IN %s AND (NOT read_user_ids@>ARRAY[%s] OR read_user_ids IS NULL)",int(user_id),tuple(ids),int(user_id))
        return res

    def get_num_unread(self,context={}):
        user_id=access.get_active_user()
        if not user_id:
            return None
        all_ids=get_model("chat.message").search([]) # XXX
        if not all_ids:
            return 0
        db=database.get_connection()
        min_t=(datetime.today()-timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        res=db.get("SELECT COUNT(*) AS num_unread FROM chat_message WHERE id IN %s AND (NOT read_user_ids@>ARRAY[%s] OR read_user_ids IS NULL) AND time>=%s",tuple(all_ids),user_id,min_t)
        return res.num_unread or 0

ChatMessage.register()
