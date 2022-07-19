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

import tornado.ioloop
import tornado.httpserver
import tornado.web
from . import controller
from . import config
from . import module
from . import static
from . import database
import argparse
from . import model
from . import locale
from . import action
from . import layout
from . import test
from . import migration
from . import log
from . import tasks
from . import queue
from multiprocessing import Process
import platform
import netforce
import os
import time
from .utils import print_color
try:
    import psutil
except:
    print("WARNING: failed to import psutil")
from . import ipc
import signal

NUM_PROCESSES = 0


def check_signals():
    ipc.check_signals()


def web_manager():
    handlers = controller.get_handlers()
    settings = {
        "static_handler_class": static.StaticHandler,
        "static_path": "static",
    }
    app = tornado.web.Application(handlers, **settings)
    server = tornado.httpserver.HTTPServer(app, xheaders=True)
    server.bind(int(config.get("port")))
    print("Listening on port %s..." % config.get("port"))
    if platform.system() == "Windows":  # XXX
        server.start()
    else:
        if not config.DEV_MODE:
            num_procs=NUM_PROCESSES or int(config.get("web_processes"))
        else:
            num_procs=1
        server.start(num_procs)
    cb = tornado.ioloop.PeriodicCallback(check_signals, 1000)
    cb.start()
    tornado.ioloop.IOLoop.instance().start()


def load_modules(modules):
    print("loading modules...")
    for mod in modules:
        module.load_module(mod)

_version_name = None
_version_code = None

def set_module_version(version_name,version_code):
    global _version_name,_version_code
    _version_name=version_name
    _version_code=version_code


def get_module_version_name():
    return _version_name

def get_module_version_code():
    return _version_code

web_proc=None

def on_sigterm(signum,frame):
    print("Received SIGTERM pid=%s"%os.getpid())
    print("Kill all child processes...")
    root = psutil.Process(os.getpid())
    sub_pids=[]
    for child in root.get_children(recursive=True):
        sub_pids.append(child.pid)
    print("kill sub_pids",sub_pids)
    for pid in sub_pids:
        try:
            proc=psutil.Process(pid)
            proc.kill()
        except Exception as e:
            print("WARNING: failed to kill process %s: %s"%(pid,e))
    print("#"*80)
    print("ALL CHILD PROCESS KILLED, KILLING ROOT PROCESS IN 5 SECONDS...")
    print("#"*80)
    time.sleep(5);
    root.kill()

def run_server():
    global NUM_PROCESSES
    parser = argparse.ArgumentParser(description="Netforce server")
    parser.add_argument("-v", "--version", action="store_true", help="Show version information")
    parser.add_argument("-d", "--db", metavar="DB", help="Database")
    parser.add_argument("-s", "--schema", metavar="SCHEMA", help="Database schema")
    parser.add_argument("-t", "--tasks", action="store_true", help="Run background tasks")
    parser.add_argument("-q", "--queue", metavar="QUEUE", help="Process messages from external queue")
    parser.add_argument("-u", "--update", action="store_true", help="Update database schema")
    parser.add_argument("-M", "--migrate", metavar="FROM_VERSION", help="Apply version migrations")
    parser.add_argument("-l", "--load", metavar="MODULE", help="Load module data")
    parser.add_argument("-S", "--export_static", action="store_true", help="Update static files")
    parser.add_argument("-T", "--test", action="store_true", help="Run unit tests")
    parser.add_argument("-D", "--devel", action="store_true", help="Development mode")
    parser.add_argument("-f", "--force", action="store_true", help="Force")
    parser.add_argument("-p", "--num_proc", metavar="NUM", type=int, help="Number of processes to use")
    args = parser.parse_args()
    NUM_PROCESSES = args.num_proc
    config.DEV_MODE = args.devel
    if config.DEV_MODE:
        print("running in development mode...")
    config.load_config()
    if args.version:
        version = get_module_version_name()
        print(version)
        return
    dbname = args.db or config.get("database")
    if dbname:
        database.set_active_db(dbname)
    schema = args.schema or config.get("schema")
    if schema:
        database.set_active_schema(schema)
    ipc.init()
    if args.update:
        with database.Transaction():
            model.update_db(force=args.force)
        return
    if args.migrate is not None:
        migration.apply_migrations(from_version=args.migrate)
        db = database.get_connection()
        db.commit()
        return
    if args.export_static:
        static.export_static()
        return
    if args.test:
        test.run_tests()
        return
    tasks.init_tasks()
    if args.tasks:
        tasks.run_tasks()
        return
    if args.queue:
        queue.read_queue(args.queue)
        return
    locale.load_translations()
    action.load_actions()
    layout.load_xml_layouts()
    static.make_ui_params()
    model.init_js()
    t=time.strftime("%Y-%m-%dT%H:%M:%S")
    line="[%s] server started\n"%t
    open("/tmp/nf_start.log","a").write(line)
    web_manager()
