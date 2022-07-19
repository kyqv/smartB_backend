from netforce.model import Model, fields, get_model
from netforce import database, utils
from netforce import tasks
from netforce import tracer
from datetime import *
import time
import json
import traceback


class Msg(Model):
    _name = "queue.message"
    _string = "Queue Message"
    _fields = {
        "queue_id": fields.Many2One("queue", "Queue", required=True, on_delete="cascade", search=True),
        "time_received": fields.DateTime("Received Time", required=True, search=True),
        "time_processed": fields.DateTime("Processed Time"),
        "body": fields.Text("Body", search=True),
        "state": fields.Selection(
            [["new", "New"], ["processed", "Processed"], ["error", "Error"]], "Status", required=True, search=True
        ),
        "result": fields.Text("Result", search=True),
        "error": fields.Text("Error", search=True),
    }
    _order = "id desc"
    _defaults = {
        "time_received": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "state": "new",
    }

    def process_message(self, ids, context={}):
        obj = self.browse(ids[0])
        queue = obj.queue_id
        data = json.loads(obj.body)
        res = get_model(queue.model).exec_func(queue.method, [data], {})

Msg.register()
