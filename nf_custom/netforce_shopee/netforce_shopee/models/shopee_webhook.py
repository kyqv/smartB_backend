from netforce.model import Model, fields, get_model
from netforce import access
from netforce import tasks
import time
from datetime import datetime
import json

class Webhook(Model):
    _name = "shopee.webhook"
    _string = "Shopee Webhook"
    _fields = {
        "date": fields.DateTime("Date",search=True),
        "body": fields.Text("Body",search=True),
        "processed_time": fields.DateTime("Processed Time", search=True),
        "state": fields.Selection([["new","New"],["done","Done"],["error","Error"]],"Status", search=True),
        "error": fields.Text("Error")
    }
    _order = "date DESC"
    _defaults = {
        "state": "new",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    def create(self,vals,context={}):
        if not vals.get("state"):
            vals["state"] = "new"
        return super().create(vals,context=context)

    def handle_webhook(self,ids,context={}):
        access.set_active_user(1)
        job_id = context.get("job_id")
        i = 0
        for obj in self.browse(ids):
            if job_id:
                if tasks.is_aborted(job_id):
                    return
                tasks.set_progress(job_id,i,"Processing %s of %s Entries"%(i,len(ids)))
            try:
                if not obj.body:
                    raise Exception("No Body")
                body = json.loads(obj.body)
                code = body.get("code")
                if code is None:
                    raise Exception("Code not in Body")
                shop_id = body.get("shop_id")
                if not shop_id:
                    raise Exception("shop_id not found in Body")
                res = get_model("shopee.account").search_browse([["shop_idno","=",str(shop_id)]])
                if res.company_id:
                    access.set_active_company(company_id.id)
                if not res:
                    raise Exception("Shopee Account not found with ID %s"%shop_id)
                acc = res[0]
                if code == 0:
                    pass
                elif code ==  3:
                    data = body.get("data")
                    if not data:
                        raise Exception("data not found in Body")
                    order_sn = data.get("ordersn")
                    if not order_sn:
                        raise Exception("order_sn not found in data")
                    order_id = acc.get_order(order_sn)
                    if order_id and data["status"]:
                        order = get_model("shopee.order").browse(order_id)
                        order.trigger(data["status"])
                    obj.write({
                       "state": "done",
                       "processed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       "error": None,
                    })
                elif code ==  4:
                    data = body.get("data")
                    if not data:
                        raise Exception("data not found in Body")
                    order_sn = data.get("ordersn")
                    if not order_sn:
                        raise Exception("order_sn not found in data")
                    order_id = acc.get_order(order_sn)
                    order = get_model("shopee.order").browse(order_id)
                    # orders = get_model("shopee.order").search_browse([["order_sn","=",order_sn]])
                    if order:
                        # order = orders[0]
                        order.write({
                            "tracking_number": data.get("tracking_no"),
                            "package_number": data.get("package_number"),
                        })
                        if order.pickings:
                            for pick in order.pickings:
                                pick.write({"ship_tracking": data.get("tracking_no")})
                        else:
                            logs = order.logs or ""
                            log = "%s :shopee.webhook.handle_webhook\n" % datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            log += "Picking not found"
                            log += "-" * 10
                            log += "\n\n"
                            logs = log + logs
                            order.write({"logs":logs})
                        order.trigger("UPDATE_TRACKING")
                    obj.write({
                       "state": "done",
                       "processed_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                       "error": None,
                    })

            except Exception as e:
                obj.write({
                    "state":"error",
                    "error":str(e),
                    "processed_time":datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
            i += 1

Webhook.register()
