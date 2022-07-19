# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce.model import Model, fields, get_model
from netforce import access
from netforce import config
from netforce import database
from netforce import utils
from pprint import pprint
import string
import random
try:
    import pyotp
except:
    print("WARNING: failed to import pyotp")


class User(Model):
    _name = "base.user"
    _key = ["login"]
    _string = "User"
    _audit_log=True
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "login": fields.Char("Login", required=True, search=True),
        "code": fields.Char("Code", search=True),
        "password": fields.Char("Password", password=True, size=256),
        "email": fields.Char("Email", search=True),
        "mobile": fields.Char("Mobile"),
        "role_id": fields.Many2One("role", "Role"),
        "profile_id": fields.Many2One("profile", "Profile", required=True, search=True),
        "lastlog": fields.DateTime("Last login"),
        "active": fields.Boolean("Active"),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "online_status": fields.Selection([["offline", "Offline"], ["online", "Online"]], "Status", function="get_online_status"),
        "contact_id": fields.Many2One("contact", "Contact"),
        "pin_code": fields.Char("PIN Code", size=256),
        "company_id": fields.Many2One("company","Company",search=True, required=True), # Chin Added required
        "company2_id": fields.Many2One("company","Company #2",search=True),
        "password_reset_code": fields.Char("Password Reset Code"),
        "num_unread_messages": fields.Integer("# Unread Messages",function="get_num_unread_messages"),
        "image": fields.File("Picture"),
        "first_name": fields.Char("First Name", search=True),
        "last_name": fields.Char("Last Name", search=True),
        "full_name": fields.Char("Full Name", function="get_full_name"),
        "device_tokens": fields.One2Many("device.token","user_id","Device Tokens"),
        "show_timer": fields.Boolean("Show Timer"),
        "hourly_rate": fields.Decimal("Hourly Rate"),
        "num_new_notifs": fields.Integer("# New Notifs",function="get_num_new_notifs"),
        "otp_secret": fields.Char("OTP Secret"),
        "otp_enabled": fields.Boolean("OTP Enabled",function="get_otp_enabled"),
        "product_id": fields.Many2One("product","Product"),
        "products": fields.Many2Many("product","Other Products"),
        "state": fields.Selection([["wait_approve","Awaiting Approval"],["approved","Approved"],["rejected","Rejected"]],"Status"),
        "sig_image": fields.File("Signature Image"),
        "regions": fields.Many2Many("region", "Regions"),
        "prevent_multi_login": fields.Boolean("Prevent Concurrent Logins"),
    }
    _order = "login"
    _defaults = {
        "activ_code": lambda *a: "%.x" % random.randint(0, 1 << 32),
        "active": True,
    }

    def name_search(self, name, condition=[], limit=None, context={}):
        cond = [["or", ["name", "ilike", "%" + name + "%"], ["login", "ilike", "%" + name + "%"]], condition]
        ids = self.search(cond, limit=limit)
        return self.name_get(ids, context)

    def disable_users(self, context={}):
        max_users = self.get_max_users()
        if max_users is None:
            return
        db = database.get_connection()
        num_users = db.get("SELECT COUNT(*) FROM base_user WHERE active").count
        if num_users <= max_users:
            return
        res = db.get("SELECT id FROM base_user WHERE active ORDER BY id OFFSET %d LIMIT 1" % max_users)
        user_id = res.id
        db.execute("UPDATE base_user SET active=false WHERE id>=%d" % user_id)

    def delete(self, ids, **kw):
        if 1 in ids:
            raise Exception("Can not delete root user (id=1)")
        super().delete(ids, **kw)

    def send_activ_email(self, ids, context={}):
        res = get_model("email.account").search([["type", "=", "smtp"]])
        if not res:
            raise Exception("Email account not found")
        smtp_id = res[0]
        for user in self.browse(ids):
            from_addr = "support@netforce.com"
            to_addr = user.email
            subject = "Welcome to Netforce!"
            body = """Welcome to Netforce and thanks for signing up!

Click on the link below to activate your account.
http://nf1.netforce.com/action?name=nfw_activate&activ_code=%s""" % user.activ_code
            vals = {
                "type": "out",
                "account_id": smtp_id,
                "from_addr": from_addr,
                "to_addr": to_addr,
                "subject": subject,
                "body": body,
            }
            msg_id = get_model("email.message").create(vals)
            get_model("email.message").send([msg_id])

    def send_password_reset_email(self, ids, context={}):
        res = get_model("email.account").search([["type", "=", "smtp"]])
        if not res:
            raise Exception("Email account not found")
        smtp_id = res[0]
        for user in self.browse(ids):
            code = "%.x" % random.randint(0, 1 << 32)
            user.write({"reset_code": code})
            from_addr = "support@netforce.com"
            to_addr = user.email
            subject = "Netforce password reset"
            body = """Click on the link below to reset your password.
http://nf1.netforce.com/action?name=nfw_reset_passwd&reset_code=%s""" % code
            vals = {
                "type": "out",
                "account_id": smtp_id,
                "from_addr": from_addr,
                "to_addr": to_addr,
                "subject": subject,
                "body": body,
            }
            msg_id = get_model("email.message").create(vals)
            get_model("email.message").send([msg_id])

    def get_online_status(self, ids, context={}):
        vals = {}
        db = database.get_connection()
        res = db.query("SELECT user_id FROM ws_listener")
        online_ids = set([r.user_id for r in res])
        for obj in self.browse(ids):
            vals[obj.id] = obj.id in online_ids and "online" or "offline"
        return vals

    def check_password(self, login, password, context={}):
        db = database.get_connection()
        res = db.get("SELECT id,password FROM base_user WHERE login ILIKE %s", login)
        if not res:
            return None
        if not utils.check_password(password, res.password):
            return None
        return res.id

    def get_enc_password(self, context={}):
        db = database.get_connection()
        res = db.query("SELECT id,login,name,profile_id,password,company_id FROM base_user where active=true")
        if not res:
            return None
        return res

    def check_pin_code(self, ids, pin_code, context={}):
        user_id = ids[0]
        db = database.get_connection()
        res = db.get("SELECT pin_code FROM base_user WHERE id=%s", user_id)
        if not res:
            return None
        if not utils.check_password(pin_code, res.pin_code):
            return None
        return True

    def get_ui_params(self, context={}):
        user_id = access.get_active_user()
        if not user_id:
            return
        try:
            access.set_active_user(1)
            db = database.get_connection()
            if not db:
                return
            user = self.browse(user_id)
            params = {
                "name": user.name,
            }
            prof = user.profile_id
            params["default_model_perms"] = prof.default_model_perms
            params["model_perms"] = []
            for p in prof.perms:
                params["model_perms"].append({
                    "model": p.model_id.name,
                    "perm_read": p.perm_read,
                    "perm_create": p.perm_create,
                    "perm_write": p.perm_write,
                    "perm_delete": p.perm_delete,
                })
            params["field_perms"] = []
            for p in prof.field_perms:
                params["field_perms"].append({
                    "model": p.field_id.model_id.name,
                    "field": p.field_id.name,
                    "perm_read": p.perm_read,
                    "perm_write": p.perm_write,
                })
            params["default_menu_access"] = prof.default_menu_access
            params["menu_perms"] = []
            for p in prof.menu_perms:
                params["menu_perms"].append({
                    "action": p.action,
                    "menu": p.menu,
                    "access": p.access,
                })
            params["other_perms"] = [p.code for p in prof.other_perms]
            return params
        finally:
            access.set_active_user(user_id)
    

    def password_reset(self,ids,context={}):
        obj = self.browse(ids)
        random_no ="%012d"%random.randint(0,999999999999) 
        obj.write({'password_reset_code':random_no})
        return random_no

    def get_num_unread_messages(self,ids,context={}):
        db=database.get_connection()
        res=db.query("SELECT to_id,COUNT(*) FROM message WHERE state='new' GROUP BY to_id")
        nums={}
        for r in res:
            nums[r.to_id]=r.count
        vals={}
        for user_id in ids:
            vals[user_id]=nums.get(user_id,0)
        return vals

    def get_num_new_notifs(self,ids,context={}):
        user_id=ids[0]
        vals={}
        res=get_model("notif").search([["show_board","=",True]]) # XXX: speed?
        vals[user_id]=len(res)
        return vals

    def get_full_name(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            if obj.first_name:
                name=obj.first_name or "N/A"
                if obj.last_name:
                    name+=" "+obj.last_name
            else:
                name=obj.name or "N/A"
            vals[obj.id]=name
        return vals

    def view_user_pref(self,context={}):
        user_id=access.get_active_user()
        return {
            "next": {
                "name": "user_pref",
                "active_id": user_id,
            },
        }

    def new_password_reset_code(self,ids,context={}):
        obj=self.browse(ids[0])
        code = "%.x" % random.randint(0, 1 << 32)
        obj.write({"password_reset_code": code})

    def get_otp_enabled(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=True if obj.otp_secret else False
        return vals

    def change_password(self, password, new_password, context={}):
        if not password:
            raise Exception("Missing current password")
        if not new_password:
            raise Exception("Missing new password")
        user_id=access.get_active_user()
        if not user_id:
            raise Exception("Missing user_id")
        user=self.browse(user_id)
        res = self.check_password(user.login, password)
        if not res:
            raise Exception("Wrong password")
        access.set_active_user(1)
        if len(new_password) < 4:
            raise Exception("Password has to be at least 4 characters long")
        self.write([user_id],{"password": new_password})
        access.set_active_user(user_id)

    def get_new_otp(self,context={}):
        user_id=access.get_active_user()
        user=get_model("base.user").browse(user_id)
        otp_secret=pyotp.random_base32()
        otp_url=pyotp.totp.TOTP(otp_secret).provisioning_uri(user.login, "HydraX") # XXX
        vals={
            "otp_secret": otp_secret,
            "otp_url": otp_url,
        }
        return vals
        
    def set_otp(self,password,otp_secret,otp_token,context={}):
        if not password:
            raise Exception("Missing password")
        if not otp_secret:
            raise Exception("Missing OTP secret")
        if not otp_token:
            raise Exception("Missing OTP token")
        user_id=access.get_active_user()
        user=self.browse(user_id)
        res = self.check_password(user.login, password)
        if not res:
            raise Exception("Wrong password")
        totp = pyotp.TOTP(otp_secret)
        if not totp.verify(otp_token):
            raise Exception("Invalid 2FA token")
            #raise Exception("Invalid 2FA token ('%s' / '%s' / '%s')"%(otp_token,totp.now(),otp_secret))
        user.write({"otp_secret": otp_secret})

    def disable_otp(self,password,otp_token,context={}):
        if not password:
            raise Exception("Missing password")
        user_id=access.get_active_user()
        user=self.browse(user_id)
        res = self.check_password(user.login, password)
        if not res:
            raise Exception("Wrong password")
        if not user.otp_secret:
            raise Exception("OTP not enabled")
        totp = pyotp.TOTP(user.otp_secret)
        if not totp.verify(otp_token):
            raise Exception("Invalid 2FA token")
        user.write({"otp_secret": None})

    def approve(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state":"approved"})
            obj.trigger("approved")

    def reject(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state":"rejected"})
            obj.trigger("rejected")

User.register()
