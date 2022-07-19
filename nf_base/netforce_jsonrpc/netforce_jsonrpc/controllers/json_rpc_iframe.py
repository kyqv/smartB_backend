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

from netforce.controller import Controller
from netforce.model import get_model, clear_cache
from netforce import database
from netforce import access
import json
import traceback
import sys
import time
import random
from netforce.locale import translate
from netforce.utils import timeout,json_dumps
from netforce.log import rpc_log
import urllib.parse


class JsonRpcIframe(Controller):
    _path = "/json_rpc_iframe"

    def post(self):
        req = json.loads(urllib.parse.unquote(self.get_argument("request")))
        db = database.get_connection()
        if db:
            db.begin()
        try:
            clear_cache()
            method = req["method"]
            params = req["params"]
            if method == "execute":
                model = params[0]
                method = params[1]
                if method.startswith("_"):
                    raise Exception("Invalid method")
                args = params[2]
                if len(params) >= 4:
                    opts = params[3] or {}
                else:
                    opts = {}
                user_id = access.get_active_user()
                rpc_log.info("EXECUTE db=%s model=%s method=%s user=%s" %
                             (database.get_active_db(), model, method, user_id))
                m = get_model(model)
                f = getattr(m, method)
                ctx = {
                    "request_handler": self,
                    "request": self.request,
                }
                ctx.update(self.get_cookies())
                opts.setdefault("context", {}).update(ctx)
                with timeout(seconds=300):  # XXX: can make this faster? (less signal sys handler overhead)
                    t0 = time.time()
                    res = f(*args, **opts)
                    t1 = time.time()
                    dt = (t1 - t0) * 1000
                    rpc_log.info("<<< %d ms" % dt)
                resp = {
                    "result": res,
                    "error": None,
                    "id": req["id"],
                }
            else:
                raise Exception("Invalid method: %s" % method)
            db = database.get_connection()
            if db:
                db.commit()
        except Exception as e:
            try:
                msg = translate(str(e))
            except:
                print("WARNING: Failed to translate error message")
                msg = str(e)
            rpc_log.error(msg)
            db = database.get_connection()
            if db:
                db.rollback()
            rpc_log.error(traceback.format_exc())
            err = {
                "message": msg,
            }
            error_fields = getattr(e, "error_fields", None)
            if error_fields:
                err["error_fields"] = error_fields
            resp = {
                "result": None,
                "error": err,
                "id": req["id"],
            }
        access.clear_active_user()
        try:
            data = urllib.parse.quote(json_dumps(resp))
        except:
            print("JSONRPC ERROR: invalid response")
            from pprint import pprint
            pprint(resp)
        print("json_rpc_iframe result", data)
        self.write(data)

JsonRpcIframe.register()
