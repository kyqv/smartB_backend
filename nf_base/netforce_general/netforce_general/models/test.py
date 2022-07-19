from netforce.model import Model, fields, get_model
from netforce.database import get_connection
from netforce import utils
from netforce import database
from netforce import access
from datetime import *
import time
import requests
import multiprocessing
import os
import subprocess
try:
    import shutil
except:
    print("Failed to import shutil")
try:
    import psutil
except:
    print("Failed to import psutil")

class Test(Model):
    _name = "test"
    _store=False

    def check_disk_space(self,context={}):
        res=shutil.disk_usage("/")
        pct=int(res.used*100/res.total)
        if pct<90:
            return "OK (%s%% used, %s / %s)"%(pct,utils.format_file_size(res.used),utils.format_file_size(res.total))
        return "not enough available disk space (%s%% used)"%pct

    def check_memory(self,restart=False,context={}):
        mem=psutil.virtual_memory()
        used=mem.total-mem.available
        pct=int(used*100/mem.total)
        if pct<90:
            return "OK (%s%% used, %s / %s)"%(pct,utils.format_file_size(used),utils.format_file_size(mem.total))
        if restart:
            os.system("killall -9 python")
        return "not enough available memory (%s%% used)"%pct

    def check_cpu(self,context={}):
        pct=psutil.cpu_percent(interval=None)
        count=multiprocessing.cpu_count()
        if pct<90:
            return "OK (%s%% used, %s cpu cores)"%(pct,count)
        return "CPU usage too high (%s%%)"%pct

    def check_load_avg(self,context={}):
        res=os.getloadavg()
        if res[1]>0.4:
            return "load average too high (1min=%s%% 5min=%s%% 15min=%s$$)"%(int(res[0]*100),int(res[1]*100),int(res[2]*100))
        return "OK (1min=%s%% 5min=%s%% 15min=%s%%)"%(int(res[0]*100),int(res[1]*100),int(res[2]*100))

    def check_swap(self,context={}):
        mem=psutil.swap_memory()
        pct=int(mem.used*100/mem.total if mem.total else 0)
        if mem.total>500*1000*1000 and pct<90:
            return "OK (%s%% used, %s / %s)"%(pct,utils.format_file_size(mem.used),utils.format_file_size(mem.total))
        return "not enough swap memory (%s%% used, %s / %s)"%(pct,utils.format_file_size(mem.used),utils.format_file_size(mem.total))

    def check_db_queries(self,context={}):
        q="SELECT query FROM pg_stat_activity WHERE state IN ('idle in transaction', 'active') AND now() - xact_start >= INTERVAL '15' second"
        db=database.get_connection()
        res=db.query(q)
        if not res:
            return "OK (all database queries completed in less than 15 seconds)"
        queries=" | ".join(r.query for r in res)
        return "%s database queries running for more than 15 seconds: %s"%(len(res),queries)

    def check_report(self,context={}):
        url = "http://localhost:9990/"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code not in (200,500):
                raise Exception("Invalid status code: %s"%r.status_code)
            return "OK (report server is running)"
        except Exception as e:
            return "failed to connect to report server: %s"%str(e)

    def check_open_files(self,context={}):
        data=open("/proc/sys/fs/file-nr").read()
        n=int(data.split()[0])
        if n>10000:
            return "too many open file descriptors: %s"%n
        return "OK (%s open file descriptors)"%n

    def check_db_size(self,context={}):
        dbname=database.get_active_db()
        db=database.get_connection()
        res=db.get("SELECT pg_database_size(%s) AS size",dbname)
        size=res.size
        if size>20*1000*1000*1000:
            raise Exception("database is too big: %s"%utils.format_file_size(size))
        return "OK (%s)"%utils.format_file_size(size)

    def check_bg_tasks(self,context={}):
        access.set_active_user(1)
        t=datetime.now()-timedelta(hours=1)
        cond=[["date","<=",t],["state","=","waiting"]]
        res=get_model("bg.task").search(cond)
        if res:
            return "%s background tasks waiting for more than 1 hour"%len(res)
        return "OK (no background tasks waiting for more than 1 hour)"

    def check_slow_rpc(self,dt,minutes=15,context={}):
        dbname=database.get_active_db()
        path="/tmp/slow_rpc_%s.log"%dt
        proc = subprocess.Popen(['tail', '-n', "100", path], stdout=subprocess.PIPE)
        lines = proc.stdout.readlines()
        min_t=(datetime.now()-timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S")
        recent_lines=[]
        for l in lines:
            l=l.decode("utf8").strip()
            res=l.split()
            t=res[0][1:-1]
            db=res[1].split("=")[1]
            if db!=dbname:
                continue
            #open("/tmp/xxx.log","a").write("%s | %s | %s\n"%(l,t,min_t))
            if t>=min_t:
                if len(l)>100:
                    l=l[:100]+"..."
                recent_lines.append(l)
        if recent_lines:
            raise Exception("%s slow requests in last %s minutes:\n%s"%(len(recent_lines),minutes,"\n".join(recent_lines)))
        return "OK (no slow requests in last %s minutes)"%minutes

    def check_slow_query(self,dt,minutes=15,context={}):
        dbname=database.get_active_db()
        db=database.get_connection()
        path="/tmp/slow_query_%s.log"%dt
        proc = subprocess.Popen(['tail', '-n', "100", path], stdout=subprocess.PIPE)
        lines = proc.stdout.readlines()
        min_t=(datetime.now()-timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S")
        recent_lines=[]
        for l in lines:
            l=l.decode("utf8").strip()
            res=l.split()
            t=res[0][1:-1]
            db=res[1].split("=")[1]
            if db!=dbname:
                continue
            #open("/tmp/xxx.log","a").write("%s | %s | %s\n"%(l,t,min_t))
            if t>=min_t:
                if len(l)>200:
                    l=l[:200]+"..."
                recent_lines.append(l)
        if recent_lines:
            raise Exception("%s slow queries in last %s minutes:\n%s"%(len(recent_lines),minutes,"\n".join(recent_lines)))
        return "OK (no slow queries in last %s minutes)"%minutes

    def check_restarts(self,hours=24,context={}):
        path="/tmp/nf_start.log"
        proc = subprocess.Popen(['tail', '-n', "100", path], stdout=subprocess.PIPE)
        lines = proc.stdout.readlines()
        min_t=(datetime.now()-timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
        recent_lines=[]
        for l in lines:
            l=l.decode("utf8").strip()
            t=l.split()[0][1:-1]
            #open("/tmp/xxx.log","a").write("%s | %s | %s\n"%(l,t,min_t))
            if t>=min_t:
                recent_lines.append(l)
        return "OK (%s restarts in last %s hours)\n%s"%(len(recent_lines),hours,"\n".join(recent_lines))

    def check_mem_restart(self,minutes=5,context={}):
        path="/tmp/check_mem.log"
        proc = subprocess.Popen(['tail', '-n', "5", path], stdout=subprocess.PIPE)
        lines = proc.stdout.readlines()
        min_t=(datetime.now()-timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S")
        recent_lines=[]
        found=False
        for l in lines:
            l=l.decode("utf8").strip()
            t=l.split()[0][1:-1]
            if t>=min_t:
                found=True
        if not found:
            return "high memory restart script is not running"
        return "OK (high memory restart script is running)"

    def check_load_avg_restart(self,minutes=5,context={}):
        path="/tmp/check_load_avg.log"
        proc = subprocess.Popen(['tail', '-n', "5", path], stdout=subprocess.PIPE)
        lines = proc.stdout.readlines()
        min_t=(datetime.now()-timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S")
        recent_lines=[]
        found=False
        for l in lines:
            l=l.decode("utf8").strip()
            t=l.split()[0][1:-1]
            if t>=min_t:
                found=True
        if not found:
            return "high load average restart script is not running"
        return "OK (high load average restart script is running)"

    def check_db_cluster_size(self,context={}):
        database.set_active_db("template1")
        with database.Transaction(): 
            q="SELECT SUM(pg_database_size(datname)) AS size FROM pg_database"
            db=database.get_connection()
            res=db.get(q)
            used=int(res.size)
            total=200*1000*1000*1000
            pct=int(used*100/total)
            if pct<90:
                return "OK (%s%% used, %s / %s)"%(pct,utils.format_file_size(used),utils.format_file_size(total))
            return "not enough available disk space (%s%% used)"%pct
        
Test.register()
