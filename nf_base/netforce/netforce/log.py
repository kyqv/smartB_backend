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

import logging
from netforce import database
import os
import time
from netforce.utils import format_color


class AppLogDBHandler(logging.StreamHandler):

    def emit(self, record):
        msg = self.format(record)
        dbname = database.get_active_db()
        if dbname:
            dir_path = os.path.join("static", "db", dbname, "log")
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            day = time.strftime("%Y-%m-%d")
            log_path = os.path.join(dir_path, "netforce-application-%s.log" % day)
            open(log_path, "a").write(msg + "\n")


class RPCLogDBHandler(logging.StreamHandler):

    def emit(self, record):
        msg = self.format(record)
        dbname = database.get_active_db()
        if dbname:
            dir_path = os.path.join("static", "db", dbname, "log")
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            day = time.strftime("%Y-%m-%d")
            log_path = os.path.join(dir_path, "netforce-rpc-%s.log" % day)
            open(log_path, "a").write(msg + "\n")


class LogFormatter(logging.Formatter):

    def __init__(self, color=False, **kw):
        super(LogFormatter, self).__init__(**kw)
        self.color = color

    def format(self, record):
        msg = super(LogFormatter, self).format(record)
        if self.color:
            if record.levelno == logging.INFO:
                msg = format_color(msg, color="blue", bright=True)
            elif record.levelno == logging.WARNING:
                msg = format_color(msg, color="yellow", bright=True)
            elif record.levelno == logging.ERROR:
                msg = format_color(msg, color="red", bright=True)
        return msg

app_log = logging.getLogger("netforce.application")
app_log.setLevel(logging.INFO)
app_log.propagate = False

h = logging.StreamHandler()
fmt = LogFormatter(fmt="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
h.setFormatter(fmt)
app_log.addHandler(h)

h = AppLogDBHandler()
fmt = LogFormatter(fmt="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
h.setFormatter(fmt)
app_log.addHandler(h)

rpc_log = logging.getLogger("netforce.rpc")
rpc_log.setLevel(logging.INFO)
rpc_log.propagate = False

h = logging.StreamHandler()
fmt = LogFormatter(fmt="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", color=True)
h.setFormatter(fmt)
rpc_log.addHandler(h)

#h = RPCLogDBHandler()
#fmt = LogFormatter(fmt="[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
#h.setFormatter(fmt)
#rpc_log.addHandler(h)
