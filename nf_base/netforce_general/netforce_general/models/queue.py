from netforce.model import Model, fields, get_model
from netforce import database
from netforce import tasks, utils
from datetime import *
import time
import json
import traceback


class Queue(Model):
    _name = "queue"
    _string = "External Queue"
    _fields = {
        "name": fields.Char("Name", required=True, search=True),
        "type": fields.Selection([["amqp", "AMQP"], ["stomp", "STOMP"], ["firebase","Firebase Realtime Database"]], "Type", required=True),
        "url": fields.Char("URL"),
        "description": fields.Char("Description"),
        "model": fields.Char("Model"),
        "method": fields.Char("Method"),
        "messages": fields.One2Many("queue.message", "queue_id", "Messages"),
    }
    _order = "name"

    def process_new(self, ids, context={}):
        obj = self.browse(ids[0])
        n = 0
        for msg in get_model("queue.message").search_browse(
            [["queue_id", "=", obj.id], ["state", "=", "new"]], order="time_received desc"
        ):
            n += 1
            try:
                data = json.loads(msg.body)
                res = get_model(obj.model).exec_func(obj.method, [data], {})
                t1 = utils.current_local_time_string()
                db = database.get_connection()
                db.execute(
                    "UPDATE queue_message SET state='processed',result=%s,time_processed=%s WHERE id=%s",
                    str(res),
                    t1,
                    msg.id,
                )
            except Exception as e:
                print("!" * 80)
                print("ERROR: %s" % e)
                err = traceback.format_exc()
                t1 = utils.current_local_time_string()
                db = database.get_connection()
                db.execute(
                    "UPDATE queue_message SET state='error',error=%s,time_processed=%s WHERE id=%s", err, t1, msg.id
                )
        return {
            "alert": "%s messages processed" % n,
        }


Queue.register()
