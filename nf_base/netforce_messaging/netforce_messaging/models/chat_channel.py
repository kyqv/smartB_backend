from netforce.model import Model,fields,get_model
from netforce import database
from netforce import access
from netforce import ipc
import time
import json

class ChatChannel(Model):
    _name="chat.channel"
    _string="Chat Channel"
    _audit_log=True
    _fields={
        "name": fields.Char("Channel Name",required=True,search=True),
        "code": fields.Char("Channel Code",search=True),
        "sequence": fields.Integer("Sequence"),
        "description": fields.Char("Channel Description",search=True),
        "user_id": fields.Many2One("base.user","Created By"),
        "messages": fields.One2Many("chat.message","channel_id","Messages"),
        "num_messages": fields.Integer("Num Messages",function="get_num_messages"),
        "num_members": fields.Integer("Num Members",function="get_num_members"),
        "members": fields.Many2Many("base.user","Members",function="get_members"),
        "last_message_id": fields.Many2One("chat.message","Last Message",function="get_last_message"),
        "num_unread": fields.Integer("Unread Messages",function="get_num_unread"),
        "last_message_time": fields.DateTime("Last Message Time"),
    }
    _defaults={
        "time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": lambda *a: access.get_active_user(),
    }
    _order="sequence,id"

    def get_members(self,ids,context={}):
        db=database.get_connection()
        res=db.query("SELECT a.record_id,u.id AS user_id FROM record_access a JOIN base_user u ON u.email=a.email WHERE a.model='chat.channel' AND a.record_id IN %s",tuple(ids))
        users={}
        for r in res:
            users.setdefault(r.record_id,[]).append(r.user_id)
        vals={}
        for id in ids:
            vals[id]=users.get(id,[])
        return vals

    def get_num_members(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.members)
        return vals

    def get_num_messages(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.messages)
        return vals

    def get_last_message(self,ids,context={}):
        vals={}
        for obj in self.browse(ids,context=context):
            vals[obj.id]=obj.messages[-1].id if obj.messages else None
        return vals

    def get_num_unread(self,ids,context={}):
        user_id=access.get_active_user()
        unread={}
        if user_id:
            all_ids=get_model("chat.message").search([]) # XXX
            if all_ids:
                db=database.get_connection()
                res=db.query("SELECT channel_id,COUNT(*) num_unread FROM chat_message WHERE id IN %s AND NOT read_user_ids@>ARRAY[%s] OR read_user_ids IS NULL GROUP BY channel_id",tuple(all_ids),int(user_id))
                for r in res:
                    unread[r.channel_id]=r.num_unread
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=unread.get(obj.id,0)
        return vals

ChatChannel.register()
