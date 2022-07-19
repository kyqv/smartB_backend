from netforce.model import Model, fields
from netforce import access
from netforce import utils
from netforce import database
from netforce import logger
import time


class Token(Model):
    _name = "access.token"
    _string = "Access Token"
    _fields = {
        "time": fields.DateTime("Login Time", required=True, search=True),
        "ip_addr": fields.Char("IP Address", required=True, search=True),
        "user_id": fields.Many2One("base.user","User",required=True,search=True,on_delete="cascade"),
        "client_name": fields.Char("Client Name",search=True),
        "token": fields.Char("Token", required=True, search=True),
        "logout_time": fields.DateTime("Logout Time", search=True),
        "expire_time": fields.DateTime("Expiry Time", search=True),
        "state": fields.Selection([["active","Active"],["logout","Logged Out"],["expired","Expired"]],"Status",required=True,search=True),
    }
    _order = "time desc"
    _defaults={
        "time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "active",
    }

    def new_token(self,user_id,context={}):
        if access.get_active_user()!=1:
            raise Exception("Permission denie")
        dbname=database.get_active_db()
        token = utils.new_token(dbname, user_id)
        db=database.get_connection()
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        ip_addr=access.get_ip_addr()
        client_name=logger.get_client_name()
        user=db.get("SELECT prevent_multi_login FROM base_user WHERE id=%s",user_id)
        if user.prevent_multi_login:
            db.execute("UPDATE access_token SET state='expired' WHERE user_id=%s",user_id)
        db.execute("INSERT INTO access_token (time,ip_addr,user_id,client_name,token,state) VALUES (%s,%s,%s,%s,%s,%s)",t,ip_addr,user_id,client_name,token,"active")
        return token

    def logout(self,user_id,token,context={}):
        db=database.get_connection()
        res=db.get("SELECT id FROM access_token WHERE user_id=%s AND token=%s",user_id,token)
        if not res:
            raise Exception("Invalid token: %s %s"%(user_id,token))
        db.execute("UPDATE access_token SET state='logout' WHERE id=%s",res.id)

    def expire(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state":"expired"})

    def check_token_old(self,user_id,token,context={}):
        db=database.get_connection()
        res=db.get("SELECT id FROM access_token WHERE user_id=%s AND token=%s AND state='active'",user_id,token)
        if not res:
            return False
        return True

    def check_token(self,user_id,token,context={}):
        db=database.get_connection()
        res=db.get("SELECT id FROM access_token WHERE user_id=%s AND token=%s AND state='active'",user_id,token)
        if res:
            return True
        return False

Token.register()
