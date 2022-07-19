from netforce.model import Model, fields, get_model
from netforce import access
import time


class Notif(Model):
    _name = "notif"
    _string = "Notification"
    _fields = {
        "time": fields.DateTime("Time", required=True, search=True),
        "user_id": fields.Many2One("base.user", "User", required=True, search=True),
        "title": fields.Char("Title", required=True, search=True, size=4096),
        "state": fields.Selection([["pending", "Pending"], ["dismissed", "Dismissed"]], "Status", required=True, search=True),
        "related_id": fields.Reference([],"Related To"),
        "type": fields.Selection([],"Type"),
        "show_board": fields.Boolean("Show On Dashboard",store=False,function_search="search_show_board"),
        "is_overdue": fields.Boolean("Is Overdue",function="get_is_overdue"),
    }
    _order = "time"
    _defaults = {
        "time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "pending",
    }

    def search_show_board(self,clause,context={}):
        t=time.strftime("%Y-%m-%d %H:%M:%S")
        user_id=access.get_active_user()
        cond=[["time","<=",t],["user_id","=",user_id],["state","=","pending"]]
        return cond

    def dismiss(self,ids,context={}):
        for obj in self.browse(ids):
            obj.write({"state":"dismissed"})
        return {
            "trigger": "reload_user",
        }

    def dismiss_all(self,ids,context={}):
        #ids=self.search([["show_board","=",True]])
        for obj in self.browse(ids):
            obj.write({"state":"dismissed"})
        return {
            "trigger": "reload_user",
        }

    def dismiss_all2(self,context={}):
        ids=self.search([["show_board","=",True]])
        for obj in self.browse(ids):
            obj.write({"state":"dismissed"})
        return {
            "trigger": "reload_user",
        }

Notif.register()
