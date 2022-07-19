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

from . import config
import psycopg2
from urllib.parse import urlparse
import sys
import time
import os


def print_color(msg, color=None):  # XXX: can't import
    if not sys.stdout.isatty():
        print(msg)
        return
    color_codes = {
        "black": 0,
        "red": 1,
        "green": 2,
        "yellow": 3,
        "blue": 4,
        "magenta": 5,
        "cyan": 6,
        "white": 7,
    }
    head = "\x1b[3%dm" % color_codes.get(color, 7)
    foot = "\x1b[39;49m"
    print(head + msg + foot)

def log_slow_query(dbname,min_dt,dt,cr,query,args):
    t=time.strftime("%Y-%m-%dT%H:%M:%S")
    f=open("/tmp/slow_query_%s.log"%min_dt,"a")
    q=cr.mogrify(query,tuple(args))
    q=q[:10000] # XXX
    line="[%s] db=%s dt=%s query=%s\n"%(dbname,t,dt,q)
    f.write(line)

MAX_CONS = 10

types_mapping = {
    'date': (1082,),
    'time': (1083,),
    'timestamp': (1114, 1184),
}

for name, typeoid in types_mapping.items():
    psycopg2.extensions.register_type(psycopg2.extensions.new_type(typeoid, name, lambda x, cr: x))

connections = {}
active_db = None
con_id=0

def connect(dbname):
    print("DB.connect db=%s pid=%s"%(dbname,os.getpid()))
    try:
        if dbname in connections:
            return connections[dbname]
        if len(connections) >= MAX_CONS:
            print_color("need to close oldest connection (pid=%s, num_cons=%s)" %
                        (os.getpid(), len(connections)), "red")
            print("existing connections: %s" % ",".join(sorted([x for x in connections.keys()])))
            close_oldest_connection()
        url = config.get_db_url(dbname)
        res = urlparse(url)
        args = {
            "host": res.hostname,
            "database": res.path[1:],
        }
        if res.port:
            args["port"] = res.port
        if res.username:
            args["user"] = res.username
        if res.password:
            args["password"] = res.password
        db = Connection(**args)
        print("  => con_id=%s"%db.con_id)
        db._dbname = dbname
        connections[dbname] = db
        return db
    except Exception as e:
        import traceback
        traceback.print_exc(file=sys.stdout)
        raise Exception("Failed to connect: %s" % e)


def set_active_db(dbname):
    global active_db
    active_db = dbname

def get_active_db():
    return active_db

def get_connection():
    #print("DB.get_connection db=%s"%active_db)
    if not active_db:
        return None
    db = connections.get(active_db)
    if db:
        if db.is_closed():
            del connections[active_db]
            db = None
        elif db.pid!=os.getpid():
            print("!"*80)
            print("WARNING: received db connection from another process (%d / %d)"%(db.pid,os.getpid()))
            del connections[active_db]
            db = None
    if not db:
        db = connect(active_db)
    #print("db.get_connection db=%s pid=%s back_pid=%s"%(active_db,os.getpid(),db._db.get_backend_pid()))
    return db

class Transaction:
    def __enter__(self):
        self.db=get_connection()
        self.db.begin()

    def __exit__(self,ex_type,ex_val,tb):
        if ex_type is None:
            self.db.commit()
        else:
            self.db.rollback()

def close_oldest_connection():
    print("db.close_oldest_connection pid=%s" % os.getpid())
    oldest_time = None
    oldest_db = None
    for dbname, con in connections.items():
        if oldest_time is None or con.con_time < oldest_time:
            oldest_time = con.con_time
            oldest_db = dbname
    con = connections[oldest_db]
    con.close()


class Connection():

    def __init__(self, **args):
        global con_id
        try:
            self._db = psycopg2.connect(**args)
            # self._db.set_session(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE) # postgres out-of-shared-memory-error
            # self._db.set_session(psycopg2.extensions.ISOLATION_LEVEL_REPEATABLE_READ)
            self._db.set_session(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
            self.con_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.con_id = con_id
            con_id+=1
            self.pid=os.getpid()
        except Exception as e:
            raise Exception("failed to connect: %s" % e)

    def begin(self):
        print(">>> db.begin db=%s pid=%s back_pid=%s"%(self._dbname,os.getpid(),self._db.get_backend_pid()))
        if self.is_closed():
            raise Exception("Connection is closed")
        try:
            res = self._db.get_transaction_status()
            if res != psycopg2.extensions.TRANSACTION_STATUS_IDLE:
                raise Exception("Failed to start transaction (%d)" % res)
            #if self._schema: # XXX: deprecated
            #    self.execute("SET search_path TO %s"%self._schema)
        except Exception as e:
            print_color("WARNING: failed to start database transaction, closing connection (db=%s, pid=%s)" %
                        (self._dbname, os.getpid()), "red")
            self.close()
            raise e

    def execute(self, query, *args):
        #print("DB.execute con_id=%s db=%s q=%s"%(self.con_id,self._dbname,query))
        if self.is_closed():
            raise Exception("Connection is closed")
        t0 = time.time()
        try:
            cr = self._db.cursor()
            if args:
                cr.execute(query, args)
            else:
                cr.execute(query)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print_color("WARNING: failed to execute database query, closing connection (db=%s, pid=%s)" %
                        (self._dbname, os.getpid()), "red")
            print("QUERY:", query)
            #print("ARGS:", args)
            self.close()
            raise e
        finally:
            t1 = time.time()
            dt = int((t1 - t0) * 1000)
            if dt>3000:
                log_slow_query(active_db,3000,dt,cr,query,args)
            elif dt>500:
                log_slow_query(active_db,500,dt,cr,query,args)
        #print("  ...done")

    def query(self, query, *args):
        #print("query",query,args)
        if self.is_closed():
            raise Exception("Connection is closed")
        t0 = time.time()
        try:
            cr = self._db.cursor()
            cr.execute(query, args)
            col_names = [d[0] for d in cr.description]
            #print("  ...done")
            return [Row(zip(col_names, r)) for r in cr]
        except Exception as e:
            import traceback
            traceback.print_exc()
            print_color("WARNING: failed to execute database query, closing connection (db=%s, pid=%s)" %
                        (self._dbname, os.getpid()), "red")
            print("QUERY:", query)
            #print("ARGS:", args)
            self.close()
            raise e
        finally:
            t1 = time.time()
            dt = int((t1 - t0) * 1000)
            if dt>3000:
                log_slow_query(active_db,3000,dt,cr,query,args)
            elif dt>500:
                log_slow_query(active_db,500,dt,cr,query,args)

    def get(self, query, *args):
        res = self.query(query, *args)
        return res and res[0] or None

    def commit(self):
        print("<<< DB.commit con_id=%s db=%s pid=%s back_pid=%s"%(self.con_id,self._dbname,os.getpid(),self._db.get_backend_pid()))
        if self.is_closed():
            raise Exception("Connection is closed")
        try:
            self._db.commit()
        except Exception as e:
            print_color("WARNING: failed to commit database transaction, closing connection (db=%s, pid=%s)" %
                        (self._dbname, os.getpid()), "red")
            self.close()
            raise e

    def rollback(self):
        print("<<< db.rollback pid=%s" % os.getpid())
        if self.is_closed():
            return
        try:
            self._db.rollback()
        except Exception as e:
            print_color("WARNING: failed to rollback database transaction, closing connection (db=%s, pid=%s)" %
                        (self._dbname, os.getpid()), "red")
            self.close()
            raise e

    def close(self):
        #print("closing database connection (db=%s, pid=%s)" % (self._dbname, os.getpid()))
        try:
            self._db.close()
        except:
            print("db connection close failed, skipping...")
            pass
        del connections[self._dbname]

    def is_closed(self):  # XXX: this only checks if connection was closed by client (not by server)...
        return self._db.closed != 0

    def fmt_query(self, query, *args):
        if not query:
            return ""
        cr = self._db.cursor()
        return cr.mogrify(query,tuple(args))

class Row(dict):

    def __getattr__(self, name):
        return self[name]


def list_databases():
    db = connect("template1")
    res = db.query("SELECT datname FROM pg_database WHERE datistemplate = false AND datname!='postgres'")
    db_list = [r.datname for r in res]
    hide = config.get("hide_databases", "")
    if hide:
        hide_dbs = [x.strip() for x in hide.split(",")]
        db_list = [x for x in db_list if x not in hide_dbs]
    db.close()
    return db_list
