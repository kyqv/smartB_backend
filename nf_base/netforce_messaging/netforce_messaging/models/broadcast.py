from netforce.model import Model,fields,get_model
from netforce import database
from netforce import access
from netforce import ipc
import json
from datetime import *
import time

class Broadcast(Model):
    _name="broadcast"
    _transient=True
    _fields={
        "channel_id": fields.Many2One("chat.channel","Channel",required=True,on_delete="cascade"),
        "profile_id": fields.Many2One("profile","Profile",required=True,on_delete="cascade"),
        "message": fields.Text("Message"),
    }

    def send(self,ids,context={}):
        obj=self.browse(ids[0])
        chan=obj.channel_id
        for user in get_model("base.user").search_browse([["profile_id","=",obj.profile_id.id]]):
            vals={
                "channel_id": chan.id,
                "message": obj.message,
                "to_user_id": user.id,
            }
            msg_id=get_model("chat.message").create(vals)
            for dev in user.device_tokens:
                vals={
                    "device_id": dev.id,
                    "title": "%s (%s)"%(user.first_name,chan.name),
                    "message": obj.message[:140],
                    "state": "to_send",
                }
                get_model("push.notif").create(vals)
        get_model("push.notif").send_notifs_async()
        return {
            "next": {
                "name": "l2g_chat",
            }
        }

Broadcast.register()
