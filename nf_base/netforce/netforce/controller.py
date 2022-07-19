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

import platform
import tornado.web
if platform.system() != "Windows":
    import tornado.websocket
import json
import base64
from . import config
from . import database
import netforce
import time
import json
from netforce.model import get_model
from . import access
import os
from netforce import utils

handlers = {}


class Controller(tornado.web.RequestHandler):
    _path = None

    @classmethod
    def register(cls):
        if not cls._path:
            raise Exception("Missing path in controller: %s" % cls.__name__)
        handlers[cls._path] = cls

    def prepare(self):
        print(">>> [%s] %s %s %d" %
              (time.strftime("%Y-%m-%d %H:%M:%S"), self.request.method, self.request.uri, os.getpid()))
        dbname = None
        if config.get("database"):
            dbname = config.get("database")
        elif config.get("database_from_domain"):
            request = self.request
            host = request.host
            subdom = host.split(".", 1)[0]
            if subdom not in ("all", "clients"):  # XXX
                dbname = subdom.replace("-", "_")
        elif config.get("database_from_http_header"):
            dbname = self.request.headers.get("X-Database")
        if not dbname:
            dbname = self.get_cookie("dbname")
        database.set_active_db(dbname)
        locale = self.get_cookie("locale") or self.request.headers.get("X-Locale") or "en_US"
        netforce.locale.set_active_locale(locale)
        user_id = self.get_cookie("user_id")
        if user_id and dbname:
            user_id = int(user_id)
            token = utils.url_unescape(self.get_cookie("token"))
            if utils.check_token(dbname, user_id, token):
                access.set_active_user(user_id)
            else:
                print("WARNING: wrong token! (dbname=%s user_id=%s token=%s)" % (dbname, user_id, token))
                self.clear_cookie("user_id")
                raise Exception("Invalid token")
        else:
            access.set_active_user(None)
        ip_addr = self.request.headers.get("X-Real-IP") or self.request.remote_ip
        access.set_ip_addr(ip_addr)
        company_id = self.get_cookie("company_id")
        if company_id:
            company_id = int(company_id)
            access.set_active_company(company_id)
        else:
            access.set_active_company(None)

    def set_flash(self, type, message, path=None):
        data = json.dumps({"type": type, "message": message, "path": path or ""})
        data = base64.urlsafe_b64encode(data.encode())
        self.set_cookie("flash", data)

    def get_flash(self):
        data = self.get_cookie("flash")
        if not data:
            return None
        data = base64.urlsafe_b64decode(data.encode())
        data = json.loads(data.decode())
        return data

    def clear_flash(self):
        self.clear_cookie("flash")

    def get_cookies(self):
        vals = {}
        for n in self.cookies:
            v = self.get_cookie(n)
            vals[n] = v
        return vals

if platform.system() != "Windows":
    class WebSocketHandler(tornado.websocket.WebSocketHandler):
        _path = None

        @classmethod
        def register(cls):
            if not cls._path:
                raise Exception("Missing path in websocket handler: %s" % cls.__name__)
            handlers[cls._path] = cls
else:
    class WebSocketHandler(object):
        _path = None

        @classmethod
        def register(cls):
            pass


def get_handlers():
    return handlers.items()
