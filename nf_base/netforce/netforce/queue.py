from netforce import database
from netforce import access
from netforce.model import get_model
from netforce import config
from netforce import tracer
from netforce import utils
import json
import time
import traceback

try:
    import pika
except:
    print("Warning: failed to import pika")
try:
    import opentracing
except:
    print("Warning: failed to import opentracing")

try:
    import firebase_admin
    from firebase_admin import credentials
except:
    print("Warning: failed to import firebase")

# XXX
cred = credentials.Certificate("/home/nf/keys/smartb-firebase.json")
firebase_admin.initialize_app(cred,{
  "databaseURL": "https://smartb-1-default-rtdb.asia-southeast1.firebasedatabase.app/"
})

queue_id = None
queue = None
url = None

def queue_callback_amqp(chan, method, properties, body):
    body_s = body.decode("utf-8")
    print("=" * 80)
    print("message", body_s)
    msg = json.loads(body_s)
    msg_id = None
    access.set_active_user(1)
    with database.Transaction():
        t0 = time.strftime("%Y-%m-%d %H:%M:%S")
        db = database.get_connection()
        res = db.get(
            "INSERT INTO queue_message (queue_id,time_received,body,state) VALUES (%s,%s,%s,'new') RETURNING id",
            queue_id,
            t0,
            body_s,
        )
        msg_id = res.id
    try:
        with database.Transaction():
            access.set_client_name("queue")
            # ctx = {"trace_id": trace_id}
            ctx = {}
            res = get_model(queue.model).exec_func(queue.method, [msg], {"context": ctx})
            t1 = utils.current_local_time_string()
            db = database.get_connection()
            db.execute(
                "UPDATE queue_message SET state='processed',result=%s,time_processed=%s WHERE id=%s",
                str(res),
                t1,
                msg_id,
            )
    except Exception as e:
        print("!" * 80)
        print("ERROR: %s" % e)
        err = traceback.format_exc()
        with database.Transaction():
            t1 = utils.current_local_time_string()
            db = database.get_connection()
            db.execute("UPDATE queue_message SET state='error',error=%s,time_processed=%s WHERE id=%s", err, t1, msg_id)

    chan.basic_ack(method.delivery_tag)

def queue_callback_firebase(event):
    print("firebase event",event.event_type,event.path,event.data)
    if event.path=="/":
        return
    msg={
        "event_type": event.event_type,
        "path": event.path,
        "data": event.data,
    }
    with database.Transaction():
        t0 = time.strftime("%Y-%m-%d %H:%M:%S")
        body_s=json.dumps(msg)
        db = database.get_connection()
        res = db.get(
            "INSERT INTO queue_message (queue_id,time_received,body,state) VALUES (%s,%s,%s,'new') RETURNING id",
            queue_id,
            t0,
            body_s,
        )
        msg_id = res.id
    try:
        with database.Transaction():
            #access.set_client_name("queue")
            # ctx = {"trace_id": trace_id}
            ctx = {}
            res = get_model(queue.model).exec_func(queue.method, [msg], {"context": ctx})
            t1 = time.strftime("%Y-%m-%d %H:%M:%S")
            db = database.get_connection()
            db.execute(
                "UPDATE queue_message SET state='processed',result=%s,time_processed=%s WHERE id=%s",
                str(res),
                t1,
                msg_id,
            )
    except Exception as e:
        print("!" * 80)
        print("ERROR: %s" % e)
        err = traceback.format_exc()
        with database.Transaction():
            t1 = time.strftime("%Y-%m-%d %H:%M:%S")
            db = database.get_connection()
            db.execute("UPDATE queue_message SET state='error',error=%s,time_processed=%s WHERE id=%s", err, t1, msg_id)

def read_queue(queue_name):
    with database.Transaction():
        access.set_active_user(1)
        access.set_active_company(1)
        res = get_model("queue").search([["name", "=", queue_name]])
        if not res:
            raise Exception("Queue not found: %s" % queue_name)
        global queue_id
        global queue
        global url
        global queue_type
        queue_id = res[0]
        queue = get_model("queue").browse(queue_id)
        url = queue.url
        if not url:
            raise Exception("Missing queue URL")
        if not queue.model:
            raise Exception("Missing queue model")
        if not queue.method:
            raise Exception("Missing queue method")
        queue_type=queue.type
        """
        if queue_type=="firebase":
            cred = credentials.Certificate("/home/ubuntu/keys/paleo-firebase.json")
            firebase_admin.initialize_app(cred,{
              "databaseURL": url,
            })
        """

    if queue_type=="amqp":
        con = None
        chan = None
        con = pika.BlockingConnection(pika.connection.URLParameters(url))
        chan = con.channel()
        chan.queue_declare(queue=queue_name)
        chan.basic_consume(queue=queue_name, on_message_callback=queue_callback)
        print(" [*] Waiting for messages. To exit press CTRL+C")
        chan.start_consuming()
    elif queue_type=="firebase":
        print(" [*] Waiting for messages. To exit press CTRL+C")
        firebase_admin.db.reference('/').listen(queue_callback_firebase)
