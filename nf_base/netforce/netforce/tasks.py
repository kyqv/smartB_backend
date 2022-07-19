from netforce import database
from netforce import access
from netforce import config
from netforce.model import get_model,init_js
from multiprocessing import Process,Event,Manager,Lock
import json
from datetime import *
import time
import os
import posix

manager=Manager()
db_tasks=manager.dict()
mutex = Lock()

task_event=Event()
MAX_WAIT=60

def process_tasks():
    while True:
        while True:
            print("db_tasks",db_tasks)
            task_event.clear()
            if not db_tasks:
                print("no tasks, waiting any db up to %.2f seconds..."%MAX_WAIT)
                task_event.wait(timeout=MAX_WAIT)
                continue
            min_date=None
            next_db=None
            for dbname,next_date in db_tasks.items():
                if not next_date:
                    continue
                if not min_date or next_date<min_date:
                    min_date=next_date
                    next_db=dbname
            if not min_date:
                print("no tasks, waiting any db up to %.2f seconds..."%MAX_WAIT)
                task_event.wait(timeout=MAX_WAIT)
                continue
            print("min_date=%s next_db=%s"%(min_date,next_db))
            d=datetime.strptime(min_date[:19],"%Y-%m-%d %H:%M:%S")
            now=datetime.now()
            if d>now:
                delay=min((d-now).total_seconds(),MAX_WAIT)
                print("next task at %s, waiting %s up to %.2f seconds..."%(min_date,next_db,delay))
                task_event.wait(timeout=delay)
                continue
            dbname=next_db
            break
        now=time.strftime("%Y-%m-%d %H:%M:%S")
        print(">"*80)
        print("[%s] check tasks %s %s"%(now,dbname,min_date))
        database.set_active_db(dbname)
        task_id=None
        print("acquiring mutex")
        mutex.acquire()
        try:
            cron_job_id=None
            with database.Transaction():
                db=database.get_connection()
                task=db.get("SELECT id,date,model,method,args,user_id,company_id,cron_job_id FROM bg_task WHERE state='waiting' ORDER BY date,id LIMIT 1")
                if task:
                    d=datetime.strptime(task.date[:19],"%Y-%m-%d %H:%M:%S")
                    now=datetime.now()
                    if d<=now:
                        task_id=task.id
                        model=task.model
                        method=task.method
                        cron_job_id=task.cron_job_id
                        args=json.loads(task.args) if task.args else {}
                        user_id=task.user_id
                        company_id=task.company_id
                        access.set_active_user(user_id or 1)
                        access.set_active_company(company_id or 1)
                        try:
                            m=get_model(model)
                            start_time=time.strftime("%Y-%m-%d %H:%M:%S")
                            print("calling method '%s'..."%method)
                            res=m.exec_func(method,[],args)
                            end_time=time.strftime("%Y-%m-%d %H:%M:%S")
                        finally:
                            access.set_active_user(1)
                        db.execute("UPDATE bg_task SET state='done',result=%s,start_time=%s,end_time=%s WHERE id=%s",str(res),start_time,end_time,task_id)
                        if cron_job_id:
                            get_model("cron.job").create_tasks([cron_job_id],context={"no_notif":True})
                    else:
                        print("WARNING: task is in the future (%s)"%dbname)
                else:
                    print("WARNING: no tasks found (%s)"%dbname)
        except Exception as e:
            print("ERROR: %s"%e)
            import traceback
            traceback.print_exc()
            time.sleep(5)
            if task_id:
                try:
                    with database.Transaction():
                        db=database.get_connection()
                        db.execute("UPDATE bg_task SET state='error',error_message=%s WHERE id=%s",str(e),task_id)
                        if cron_job_id:
                            get_model("cron.job").create_tasks([cron_job_id],context={"no_notif":True})
                except Exception as e:
                    print("ERROR2: %s"%e)
                    time.sleep(60)
        finally:
            print("releasing mutex")
            mutex.release()
        with database.Transaction():
            db=database.get_connection()
            task=db.get("SELECT date FROM bg_task WHERE state='waiting' ORDER BY date,id LIMIT 1")
            db_tasks[dbname]=task.date if task else None
            print("next_date1 %s => %s"%(dbname,db_tasks[dbname]))
        print("<"*80)

def run_tasks():
    print("#"*80)
    print("#"*80)
    print("#"*80)
    print("Waiting to receive tasks...")
    init_js()
    p=Process(target=process_tasks)
    p.start()
    res=config.get("databases")
    print("databases",res)
    if res:
        for dbname in res.split():
            dbname=dbname.strip()
            database.set_active_db(dbname)
            with database.Transaction():
                db=database.get_connection()
                task=db.get("SELECT date FROM bg_task WHERE state='waiting' ORDER BY date,id LIMIT 1")
                db_tasks[dbname]=task.date if task else None
    print("db_tasks",db_tasks)
    while True:
        try:
            with open(".nf-notify-tasks","r") as f:
                dbname=f.readline().strip()
            print("!"*80)
            print("receive notif",dbname)
            if not dbname:
                raise Exception("Missing dbname")
            time.sleep(1)
            database.set_active_db(dbname)
            with database.Transaction():
                db=database.get_connection()
                task=db.get("SELECT date FROM bg_task WHERE state='waiting' ORDER BY date,id LIMIT 1")
                db_tasks[dbname]=task.date if task else None
                print("next_date2 %s => %s"%(dbname,db_tasks[dbname]))
            print("TASK EVENT TRIGGER")
            task_event.set()
        except Exception as e:
            import traceback
            traceback.print_exc()
            print("!"*80)
            print("!"*80)
            print("!"*80)
            print("ERROR: failed to process task notification: %s"%e)
            time.sleep(5)

_job_count=None
_job_progress=None
_aborted_jobs=None

def init_tasks():
    if not os.path.exists(".nf-notify-tasks"):
        os.mkfifo(".nf-notify-tasks")
    global _job_count,_job_progress,_aborted_jobs
    manager=Manager()
    _job_count=manager.dict()
    _job_count["count"]=0
    _job_progress=manager.dict()
    _aborted_jobs=manager.dict()

def notify_task():
    print("!"*80)
    print("notify_task")
    dbname=database.get_active_db()
    if not os.path.exists(".nf-notify-tasks"):
        os.mkfifo(".nf-notify-tasks")
    fd=posix.open(".nf-notify-tasks",posix.O_RDWR) # to avoid block
    msg=(dbname+"\n").encode("utf-8")
    os.write(fd,msg)

def start_task_process(job_id,model,method,args=[],opts={}):
    print("start_task_process",job_id)
    try:
        with database.Transaction():
            m=get_model(model)
            f=getattr(m,method)
            if opts is None:
                opts={}
            ctx=opts.get("context",{})
            ctx["job_id"]=job_id
            res=f(*args,context=ctx,**opts)
            set_completed(job_id,res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        set_error(job_id,str(e))

def start_task(model,method,args=[],opts={}):
    print("!"*80)
    print("!"*80)
    print("!"*80)
    print("start_task",model,method,args,opts)
    job_id=_job_count["count"]+1
    print("job_id",job_id)
    _job_count["count"]=job_id
    p=Process(target=start_task_process,args=(job_id,model,method,args,opts))
    p.start()
    return job_id

def abort_task(job_id):
    _aborted_jobs[job_id]=True

def is_aborted(job_id):
    return _aborted_jobs.get(job_id,False)

def set_progress(job_id,percent,message=None):
    print("set_progress",job_id,percent,message)
    _job_progress[job_id]={
        "progress": percent,
        "message": message,
    }

def set_completed(job_id,result):
    print("!"*80)
    print("JOB_COMPLETED %s"%job_id)
    res=_job_progress.get(job_id,{})
    res["result"]=result
    _job_progress[job_id]=res

def set_error(job_id,error):
    res=_job_progress.get(job_id,{})
    res["error"]=error
    _job_progress[job_id]=res

def get_progress(job_id):
    return _job_progress.get(job_id)
