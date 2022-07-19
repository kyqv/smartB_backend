from netforce.model import Model, fields, get_model
import time
from netforce import access
import requests
import csv
from datetime import datetime, timedelta
import smtplib
from io import StringIO
from netforce.database import get_active_db
import os
import http.client
from netforce.logger import audit_log
from netforce.utils import get_file_path
from pprint import pprint as pp
from operator import itemgetter

def check_time(times):
    # check diff between 2 (double scan)
    res=[]
    for t in times:
        l  = datetime.strptime( t ,'%H:%M:%S')
        if not res:
            res=[t]
        else:
            # compare
            t1 = datetime.strptime( res[0] ,'%H:%M:%S')
            t2 = datetime.strptime( t ,'%H:%M:%S')
            diff =(t2-t1).seconds / 3600.0

            if diff>2.0:
                res.append(t)

    return res

class ImportAttendance(Model):
    _name="hr.import.attendance"
    _string="Import Attendance"

    _fields={
        "import_type": fields.Selection([
                                            ["auto","Auto"],
                                            ["csv","CSV"],
                                            ],"Import Type",required=True),
        "file": fields.File("CSV File"),
        "machine_id": fields.Many2One("hr.attendance.config","Machine Config"),
        "encoding": fields.Selection([["utf-8","UTF-8"],["tis-620","TIS-620"]],"Encoding",required=True),
        "date": fields.Date("Date From",required=True),
        "date_fmt": fields.Char("Date Format"),
        "comments": fields.One2Many("message","related_id","Comments"),
    }
    _order="time desc"

    def _get_machine(self,context={}):
        res=get_model("hr.attendance.config").search([[]])
        if not res:
            return None
        return res

    _defaults={
        "import_type": "auto",
        "encoding": "utf-8",
        'date_fmt': '%Y-%m-%d %H:%M:%S',
        'date': time.strftime("%Y-%m-01"),
    }

    def get_machine(self,machine_id):

        machine_ids = [machine_id]
        if not machine_id:
            # if not provide specific machine try to import all
            machine_ids = get_model("hr.attendance.config").search([[]])

        return machine_ids

    def get_remote_data(self,data):
        """
            try to connect to machine
            make sure attendance connection allow incoming from WAN/LAN
        """

        machine_ids = data['machine_ids']
        if not machine_ids:
            raise Exception("No attendance machine configured")

        yesterday = datetime.today()-timedelta(days=1)
        date =  data.get('date', yesterday.strftime("%Y-%m-01"))

        records=[]
        for mc in get_model("hr.attendance.config").browse(machine_ids):
            if mc.os_type=='zk3_0':
                records +=  self.get_remote_data_zk30({'machine_id':mc.id,'date':date})

            if mc.os_type=='zk1_5_5':
                records +=  self.get_remote_data_zk155({'machine_id':mc.id,'date':date})

        return records

    def get_remote_data_zk155(self,data):
        """
            try to connect to machine
            make sure attendance connection allow incoming from WAN/LAN
        """
        emp_obj=get_model("hr.employee")
        print('get_remote_data_zk155', data)


        yesterday = datetime.today()-timedelta(days=1)
        date_from =  data.get('date', yesterday.strftime("%Y-%m-01"))

        records=[]

        mc = get_model("hr.attendance.config").browse(data['machine_id'])

        # connect to machine
        url = "http://%s%s/%s" % (mc.ip_address,(mc.port and ":"+str(mc.port) or ""),mc.url_download)

        print('url',url)
        user=mc.user
        password=mc.password
        date_to = time.strftime("%Y-%m-%d")

        # param needs to query
        post_data={
            'uid':'extlog.dat',
        }
        r = requests.post(url, post_data, auth=(user, password))

        # get data
        res = r.content
        if not res:
            raise Exception("No Data to import")

        res = res.decode('tis-620') # this is fix encoding

        records = []
        for r in res.split('\r\n'):
            l = r.split('\t')
            print ('len', len(l))

            if len(l)!=6:
                continue

            code = l[0]
            dt = l[1]


            if dt < date_from+" 00:00:00":
                continue

            records.append({
                'code':code,
                'datetime':dt,
                'mode':'auto',
                })

        return records

    def get_remote_data_zk30(self,data):
        """
            try to connect to machine
            make sure attendance connection allow incoming from WAN/LAN
        """
        emp_obj=get_model("hr.employee")
        print('get_remote_data_zk30', data)


        yesterday = datetime.today()-timedelta(days=1)
        date_from =  data.get('date', yesterday.strftime("%Y-%m-01"))

        records=[]

        mc = get_model("hr.attendance.config").browse(data['machine_id'])

        # connect to machine
        url = "http://%s%s/%s" % (mc.ip_address,(mc.port and ":"+str(mc.port) or ""),mc.url_download)
        print( 'url',url)
        user=mc.user
        password=mc.password
        date_to = time.strftime("%Y-%m-%d")

        # param needs to query
        post_data={
            'sdate':date_from,
            'edate':date_to,
            'period':0,
            'uid':[range(1,200)], # max to 200 users
            }
        r = requests.post(url, post_data, auth=(user, password))

        # get data
        res = r.content
        if not res:
            raise Exception("No Data to import")

        res = res.decode('tis-620') # this is fix encoding

        records = []
        for r in res.split('\r\n'):
            l = r.split('\t')
            if len(l)!=5:
                continue
            code = l[0]

            dt = l[2]

            if dt < date_from+" 00:00:00":
                continue

            records.append({
                'code':code,
                'datetime':dt,
                'mode':'auto',
                })

        return records

    def process_data(self,records,date=False):
        """ convert from raw data to be use able for remote connection"""

        emp_obj=get_model("hr.employee")

        res =[]

        # TODO check with current record
        #currents = get_model("hr.attendance").search_read([
                        #['time','>=',date+ " 00:00:00"]
                        #],['employee_id','time','action'])

        #print(currents)

        employees = {}      # for Cache
        missing=[]
        for r in records:

            code = r['code']

            if not employees.get(code,False):
                employee_ids  = emp_obj.search([['attendance_code','=',code]])

                if not employee_ids:
                    # skip , if no employee
                    employee_ids  = emp_obj.search([['code','=',code]])

                if not employee_ids:
                    # skip , if no employee
                    if code not in missing:
                        missing.append(code)
                    continue

                # cache after make query for next time access
                employees[code] = employee_ids[0]

            employee_id = employees[code]

            dt = datetime.strptime( r['datetime'] ,'%Y-%m-%d %H:%M:%S')

            res.append({'employee_id':employee_id,
                        'datetime': dt.strftime('%Y-%m-%d %H:%M:00'),
                        'date':dt.strftime('%Y-%m-%d'),
                        'time':dt.strftime('%H:%M:00')})

        groups={}

        for r in res:
            groups.setdefault(r['date'],{})
            groups[r['date']].setdefault(r['employee_id'],[])

            if r['time'] not in groups[r['date']][r['employee_id']]:
                groups[r['date']].setdefault(r['employee_id'],[]).append(r['time'])
        records=[]

        for date,emp in groups.items():
            for employee_id,times in emp.items():
                #remove existing
                att_obj = get_model("hr.attendance")
                existing = att_obj.search([
                        ['employee_id','=',employee_id],
                        ['time','>=',date+" 00:00:00"],
                        ['time','<=',date+" 23:59:59"],
                        ['mode','=',"auto"],
                    ])
                att_obj.delete(existing)

                #check existing in records
                times.sort()
                times = check_time(times)


                if len(times)==1:
                    vals={
                        'employee_id':employee_id,
                        'time': date +' ' + times[0],
                        'action': 'sign_in',
                        'mode':'auto',
                        }
                    records.append(vals)

                if len(times)>1:
                    vals={
                        'employee_id':employee_id,
                        'time': date +' ' + times[0],
                        'action': 'sign_in',
                        'mode':'auto',
                        }
                    records.append(vals)
                    vals={
                        'employee_id':employee_id,
                        'time': date +' ' + times[-1],
                        'action': 'sign_out',
                        'mode':'auto',
                        }
                    records.append(vals)


        return records

    def do_import(self,data={}):
        """ allow to call from cronjob """
        att_obj = get_model("hr.attendance")

        if data.get('import_type','auto'):
            if not data.get('date',False):
                #yesterday = datetime.today()-timedelta(days=1)
                #data['date'] =  yesterday.strftime("%Y-%m-%d")

                data['date'] =  time.strftime("%Y-%m-%d")

            print("Auto import attendance...%s" % data['date'])

            machine_id = data.get('machine_ids',False)
            if not data.get('machine_ids',False):
                data['machine_ids'] = self._get_machine()

            res = self.get_remote_data( data )
            lines = self.process_data( res,data['date'] )

        else: # csv import

            res = data['csv_data']
            lines= self.process_data(res)


        for line in lines:
            employee_id = line['employee_id']
            dt = line['time']

            att_obj.create(line)

        print("Auto import attendance...DONE !")
        return True

    def prepare_csv(self,ids,context={}):

        obj=self.browse(ids)[0]

        path=get_file_path(obj.file)
        data=open(path).read()
        in_io =StringIO(data)

        dialect = csv.Sniffer().sniff(in_io.read(1024))
        in_io.seek(0)

        records=[]

        # incase of user error just put header in lower case
        for r in  csv.DictReader(in_io,dialect=dialect):
            vals={}
            for k in r.keys():
                if k.lower().startswith('emp'): # Employe
                    vals['code'] = r[k]

                if k.lower().startswith('ti'): # Time
                    vals['datetime'] = r[k]

            if vals:
                records.append(vals)

        return records

    def prepare(self,ids,context={}):
        data={}
        # get machine to process

        obj=self.browse(ids)[0]

        machine_ids = self.get_machine(obj.machine_id and obj.machine_id.id or False)
        date = obj.date

        data = { 'machine_ids':machine_ids,
                 'date': obj.date,
                'import_type' : obj.import_type,
                 }

        if obj.import_type=='csv':
            csv_data = obj.prepare_csv()
            if not csv_data:
                raise Exception("No data to import or CSV format is not correct")
            data['csv_data'] = csv_data

        return data

    def import_data(self,ids,context={}):
        obj=self.browse(ids)[0]

        data = obj.prepare()
        self.do_import(data)

        return {
            "flash": "Import Attendance Completed",
        }

ImportAttendance.register()
