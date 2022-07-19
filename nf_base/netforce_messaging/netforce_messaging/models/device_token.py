from netforce.model import Model, fields, get_model
from netforce import access
import time


class Token(Model):
    _name = "device.token"
    _string = "Device Token"
    _name_field="unique_id"
    _fields = {
        "date": fields.DateTime("Date", required=True, search=True),
        "unique_id": fields.Char("UniqueID",required=True,search=True),
        "user_id": fields.Many2One("base.user","User",search=True),
        "token": fields.Char("Notif Token",search=True),
        "model": fields.Char("Model",search=True),
        "brand": fields.Char("Brand",search=True),
        "is_tablet": fields.Boolean("Is Tablet"),
        "system_name": fields.Char("System Name",search=True),
        "system_version": fields.Char("System Version",search=True),
        "timezone": fields.Char("Timezone",search=True),
        "locale": fields.Char("Locale",search=True),
        "carrier": fields.Char("Carrier",search=True),
        "app_name": fields.Char("App Name",search=True),
        "push_notifs": fields.One2Many("push.notif","device_id","Push Notifications"),
    }
    _order = "date desc"
    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": lambda *a: access.get_active_user(),
    }

    def name_get(self,ids,context={}):
        res=[]
        for obj in self.browse(ids):
            name="%s / %s"%(obj.user_id.full_name,obj.model)
            res.append((obj.id,name))
        return res

    def register_token(self,token,app_name=None,unique_id=None,model=None,brand=None,is_tablet=None,system_name=None,system_version=None,locale=None,timezone=None,carrier=None,context={}):
        user_id=access.get_active_user()
        if not unique_id:
            raise Exception("Missing device unique ID")
        vals={
            "user_id": user_id,
            "app_name": app_name,
            "unique_id": unique_id,
            "token": token,
            "model": model,
            "brand": brand,
            "is_tablet": is_tablet,
            "system_name": system_name,
            "system_version": system_version,
            "locale": locale,
            "timezone": timezone,
            "carrier": carrier,
        }
        access.set_active_user(1)
        res=self.search([["unique_id","=",unique_id],["app_name","=",app_name]])
        if res:
            token_id=res[0]
            self.write([token_id],vals)
        else:
            self.create(vals)

Token.register()
