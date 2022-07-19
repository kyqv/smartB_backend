from netforce.controller import Controller
from netforce.model import get_model, clear_cache, LogError
from netforce import database
from netforce import access
from netforce.locale import set_active_locale
import json
import sys
from datetime import *
import time
import random
from netforce.locale import translate
from netforce.utils import timeout, json_dumps, check_token
from netforce.log import rpc_log
import traceback
from netforce import logger

TIMEOUT=120

def log_slow_rpc(dbname,min_dt,dt,model,method,args,opts,user_id,company_id):
    t=time.strftime("%Y-%m-%dT%H:%M:%S")
    f=open("/tmp/slow_rpc_%s.log"%min_dt,"a")
    line="[%s] db=%s dt=%s model=%s method=%s user_id=%s company_id=%s args=%s\n"%(t,dbname,dt,model,method,user_id,company_id,args)
    f.write(line)

def log_security(msg,user_id=None,ip_addr=None):
    t=time.strftime("%Y-%m-%dT%H:%M:%S")
    f=open("/tmp/security.log","a")
    line="[%s] user_id=%s ip_addr=%s %s\n"%(t,user_id,ip_addr,msg)
    f.write(line)

class JsonRpc(Controller):
    _path = "/json_rpc"

    def post(self):
        t0 = time.time()
        req = json.loads(self.request.body.decode())
        # open("/tmp/json_rpc.log","a").write(self.request.body.decode()+"\n###############################################################\n")
        user_id=None
        company_id=None
        model=None
        method=None
        args=None
        opts=None
        dbname=None
        try:
            clear_cache()
            method = req["method"]
            params = req["params"]
            if method == "execute":
                model = params[0]
                method = params[1]
                if method.startswith("_"):
                    raise Exception("Invalid method")
                entry_point="JSON_RPC %s %s"%(model,method)
                logger.set_entry_point(entry_point)
                args = params[2]
                if len(params) >= 4:
                    opts = params[3] or {}
                else:
                    opts = {}
                if len(params) >= 5:
                    cookies = params[4] or {}
                else:
                    cookies = {}
                if "database" in cookies:
                    dbname=cookies["database"]
                    database.set_active_db(dbname)
                if "locale" in cookies:
                    set_active_locale(cookies["locale"])
                user_id=None
                token=None
                if cookies.get("user_id"):
                    user_id=int(cookies["user_id"])
                    token=cookies.get("token")
                    dbname=database.get_active_db()
                    if not check_token(dbname, user_id, token):
                        raise LogError("Invalid access token",require_logout=True)
                access.set_access_token(token)
                print("@"*80)
                print("@"*80)
                print("@"*80)
                print("user_id",user_id)
                if user_id:
                    with database.Transaction(): # XXX: put in same trans?
                        token=access.get_access_token()
                        if not get_model("access.token").check_token(user_id,token):
                            raise LogError("Invalid access token (user_id=%s, token=%s)"%(user_id,token),type="security",require_logout=True)
                access.set_active_user(user_id)
                if cookies.get("company_id"):
                    company_id=int(cookies["company_id"])
                    access.set_active_company(company_id)
                else:
                    access.set_active_company(1) # XXX
                client_name=cookies.get("client_name")
                logger.set_client_name(client_name)
                user_id = access.get_active_user()
                rpc_log.info("EXECUTE db=%s model=%s method=%s user=%s" %
                             (database.get_active_db(), model, method, user_id))
                print("cookies",cookies)
                ctx = {
                    "request_handler": self,
                    "request": self.request,
                }
                ctx.update(self.get_cookies())
                ctx.update(cookies);
                ctx.update(opts.get("context",{}))
                opts["context"]=ctx
                with timeout(seconds=TIMEOUT):  # XXX: can make this faster? (less signal sys handler overhead)
                    with database.Transaction():
                        if user_id and not cookies.get("company_id"):
                            db=database.get_connection()
                            res=db.get("SELECT company_id FROM base_user WHERE id=%s",user_id)
                            if res:
                                company_id=res.company_id
                                if company_id:
                                    access.set_active_company(company_id)
                        m = get_model(model)
                        print("\n\nBEFORE m.exec_func():\n method=%s\n args=%s\n opts=%s\n\n"%(method,args,opts))
                        res=m.exec_func(method,args,opts)
                t1 = time.time()
                dt = int((t1 - t0) * 1000)
                resp = {
                    "result": res,
                    "error": None,
                    "id": req["id"],
                    "dt": dt,
                }
            else:
                raise Exception("Invalid method: %s" % method)
        except Exception as e:
            t1 = time.time()
            dt = int((t1 - t0) * 1000)
            try:
                msg = translate(str(e))
            except:
                print("WARNING: Failed to translate error message")
                msg = str(e)
            rpc_log.error(msg)
            rpc_log.error(traceback.format_exc())
            err = {
                "message": msg,
            }
            error_fields = getattr(e, "error_fields", None)
            if error_fields:
                err["error_fields"] = error_fields
            require_logout = getattr(e, "require_logout", None)
            if require_logout:
                err["require_logout"]=True
            resp = {
                "result": None,
                "error": err,
                "id": req["id"],
            }
        finally:
            rpc_log.info("<<< %d ms" % dt)
            if dt>5000:
                log_slow_rpc(dbname,5000,dt,model,method,args,opts,user_id,company_id)
            elif dt>1000:
                log_slow_rpc(dbname,1000,dt,model,method,args,opts,user_id,company_id)
        access.clear_active_user()
        try:
            data = json_dumps(resp)
            self.add_header("Access-Control-Allow-Origin","*")
            self.write(data)
        except:
            print("JSONRPC ERROR: invalid response")
            from pprint import pprint
            pprint(resp)
            traceback.print_exc()

    def options(self):
        self.add_header("Access-Control-Allow-Origin","*")
        self.add_header("Access-Control-Allow-Headers","Content-Type, X-Database, X-Schema, X-Locale")
        self.add_header("Access-Control-Allow-Methods","POST, GET, OPTIONS")

JsonRpc.register()
