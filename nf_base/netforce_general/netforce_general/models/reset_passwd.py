from netforce.model import Model, fields, get_model
from netforce import access


class ResetPasswd(Model):
    _name = "reset.passwd"
    _transient = True
    _fields = {
        "user_id": fields.Many2One("base.user","User"),
        "new_password": fields.Char("New Password", required=True),
        "new_password_repeat": fields.Char("Confirm Password", required=True),
        "notif": fields.Boolean("Notify User"),
    }

    def _get_user(self,context={}):
        user_id=context.get("user_id")
        if not user_id:
            user_id=access.get_active_user()
        return user_id

    _defaults={
        "user_id": _get_user,
    }

    def change_passwd(self, ids, context={}):
        obj = self.browse(ids)[0]
        if len(obj.new_password) < 4:
            raise Exception("Password has to be at least 4 characters long")
        if obj.new_password != obj.new_password_repeat:
            raise Exception("Passwords are not matching")
        user=obj.user_id
        user.write({"password": obj.new_password})
        if obj.notif:
            obj.trigger("notif")
        return {
            "alert": "Your password has been changed"
        }

ResetPasswd.register()
