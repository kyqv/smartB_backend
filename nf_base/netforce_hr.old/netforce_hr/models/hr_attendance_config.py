from netforce.model import Model, fields, get_model
import time
import requests

class AttendanceConfig(Model):
    _name="hr.attendance.config"
    _string="Attendance Config"

    _fields={
        "name":fields.Char("Attendance Config Name"),
        "ip_address":fields.Char("Hostname"),
        "url_download":fields.Char("Url Download"),
        "port":fields.Integer("Port"),
        "user":fields.Char("Username"),
        "user":fields.Char("Username"),
        "password":fields.Char("Password"),
        "comments": fields.One2Many("message","related_id","Comments"),

        "os_type": fields.Selection([
            ["zk3_0","ZK Web 3.0"],
            ["zk1_5_5","ZK Web 1.5.5"]],"Operating Software"),
    }

    def copy(self,ids,context):
        obj=self.browse(ids)[0]
        vals={
            "name": obj.name+"(Copy)",
            "ip_address": obj.ip_address,
            "url_download": obj.url_download,
            "port": obj.port,
            'user': obj.user,
            'password': obj.password,
            "comments": [],
        }
        new_id=self.create(vals)

        return {
            "next": {
                "name": "attend_config",
                "mode": "form",
                "active_id": new_id,
            },
            "flash": " Copied "
        }

    #FIXME cannot download file
    def test(self,ids,context={}):
        for obj in self.browse(ids):
            if not obj.os_type:
                continue

            url = "http://%s%s/%s" % (obj.ip_address, (obj.port and ':'+str(obj.port) or ''),obj.url_download)
            post_data={}


            if obj.os_type=='zk3_0':
                post_data={
                    'sdate':'2015-09-01',
                    'edate':'2015-09-01',
                    'period':0,
                    'uid':[range(1,1)],
                }
            elif obj.os_type=='zk1_5_5':
                post_data={
                    'uid':'extlog.dat',
                }
            else:
                raise Exception("Attendance machine yet not support")

            try:

                r = requests.post(url, post_data, auth=(obj.user, obj.password))

                flash = 'Device connected'
                if r.status_code!=200:
                    flash = 'Cannot connect : Please check configuration'

                return {
                    "next": {
                        "name": "attend_config",
                        "mode": "form",
                        "active_id":obj.id
                    },
                        "flash": flash,
                }

            except Exception as e:
                raise Exception("Error! Cannot connection (%s)"%(e))

AttendanceConfig.register()


