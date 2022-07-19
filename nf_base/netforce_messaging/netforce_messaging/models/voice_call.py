from netforce.model import Model, fields, get_model
import time

class Call(Model):
    _name = "voice.call"
    _string = "Voice Call"
    _fields = {
        "phone_from": fields.Char("From Phone",required=True,search=True),
        "phone_to": fields.Char("To Phone",required=True,search=True),
        "state": fields.Selection([["planned","Planned"],["in_progress","In Progress"],["done","Completed"],["error","Failed"]],"Status",required=True,search=True),
        "state_details": fields.Text("Status Details",search=True),
        "plan_time": fields.DateTime("Planned Time"),
        "start_time": fields.DateTime("Start Time"),
        "end_time": fields.DateTime("End Time"),
        "duration": fields.Integer("Duration (seconds)"),
        "contact_id": fields.Many2One("contact","Contact"),
        "related_id": fields.Reference([["sale.order","Sales Order"]],"Related To"),
        "description": fields.Text("Description"),
        "file": fields.File("Recording"),
        "call_id": fields.Char("Call ID",search=True), 
    }
    _order = "id desc"
    _defaults = {
        "state": "planned",
        "plan_time": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
    }

Call.register()
