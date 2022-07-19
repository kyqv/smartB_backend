from netforce.model import Model, fields
from netforce import database
import os
import os.path
try:
    import CloudFlare
except:
    print("WARNING: failed to import CloudFlare")

CF_TOKEN="XE_rM6EKmpiweouAiOM3l1eLm0ZRkrl1L7qCI3Xf"

class Database(Model):
    _name = "database"
    _store=False

    def create_db(self,dbname,template,context={}):
        if not dbname:
            raise Exception("Missing dbname")
        if not template:
            raise Exception("Missing template")
        dbname=dbname.lower().replace("-","_")
        template=template.lower().replace("-","_")
        subdom=dbname.replace("_","-")
        dom=subdom+".smartb.co"
        dbname="nfo_"+dbname
        template_dom=template.replace("_","-")+".smartb.co"
        template="nfo_"+template

        cf=CloudFlare.CloudFlare(token=CF_TOKEN)
        zone_name="smartb.co"
        res = cf.zones.get(params={'name': zone_name})
        print("zone get =>",res)
        zone_id = res[0]['id']
        print("=> zone_id",zone_id)
        params = {'name': dom, 'match':'all'}
        res = cf.zones.dns_records.get(zone_id, params=params)
        print("dns get =>",res)
        data={
            "name": subdom,
            "type": "CNAME",
            "content": "prod2.smartb.co",
        }
        if res:
            rec_id=res[0]["id"]
            cf.zones.dns_records.put(zone_id,rec_id,data=data)
        else:
            cf.zones.dns_records.post(zone_id,data=data)

        theme_dir="/home/nf/nf_base/netforce_ui_server/db_components/%s"%dbname
        if os.path.exists(theme_dir):
            raise Exception("Theme directory already exists")
        os.system("mkdir ~/nf_base/netforce_ui_server/db_components/%s"%dbname)
        os.system("cp -r ~/nf_base/netforce_ui_server/db_components/%s/%s ~/nf_base/netforce_ui_server/db_components/%s/%s"%(template,template_dom,dbname,dom))

        web_dir="/home/nf/run/static/db/%s/website"%dbname
        if os.path.exists(web_dir):
            raise Exception("Website directory already exists")
        os.system("mkdir -p ~/run/static/db/%s/website"%dbname)
        os.system("cp -r ~/run/static/db/%s/website/%s ~/run/static/db/%s/website/%s"%(template,template_dom,dbname,dom))

        database.set_active_db("template1")
        db=database.get_connection()
        db.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",template);
        db.execute("COMMIT")
        db.execute("CREATE DATABASE %s WITH TEMPLATE %s"%(dbname,template))

        url="https://%s/"%dom
        return {
            "url": url,
        }

    def delete_db(self,dbname,context={}):
        if not dbname:
            raise Exception("Missing dbname")
        dbname=dbname.lower().replace("-","_")
        dbname="nfo_"+dbname

        database.set_active_db("template1")
        db=database.get_connection()
        db.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",dbname);
        db.execute("COMMIT")
        db.execute("DROP DATABASE %s"%dbname)

Database.register()
