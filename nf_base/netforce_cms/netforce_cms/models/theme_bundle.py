from netforce.model import Model,fields,get_model
from netforce import utils
import os
import shutil
import base64
from netforce import database
import json

class Bundle(Model):
    _name="theme.bundle"
    _string="JS Bundles"
    _fields={
        "theme_id": fields.Many2One("theme","Theme",required=True,on_delete="cascade"),
        "name": fields.Char("Target File Name",required=True),
        "component_id": fields.Many2One("theme.component","Component",required=True),
    }
    _order="name"

    def gen_bundle(self,ids,context={}):
        theme_id=None
        for obj in self.browse(ids):
            if not theme_id:
                theme_id=obj.theme_id.id
            else:
                if theme_id!=obj.theme_id.id:
                    raise Exception("Different themes")
        theme=get_model("theme").browse(theme_id)
        os.system("rm -f /home/datrus/gen_bundle/components/*")
        for comp in theme.components:
            print("getting component %s..."%comp.name)
            path=os.path.join("/home/datrus/gen_bundle/components",comp.name)
            f=open(path,"w")
            f.write(comp.body)
            f.close()
        for obj in self.browse(ids):
            res=os.popen("cd /home/datrus/gen_bundle; webpack").read()
            if res.find("ERR")!=-1:
                raise Exception("Failed to generate bundle (%s): %s"%(obj.name,res))
            rand = base64.urlsafe_b64encode(os.urandom(8)).decode()
            res = os.path.splitext(os.path.basename(obj.name))
            basename, ext = res
            fname2 = basename + "," + rand + ext
            dbname = database.get_active_db()
            fdir = os.path.join("static", "db", dbname, "files")
            if not os.path.exists(fdir):
                os.makedirs(fdir)
            path = os.path.join(fdir, fname2)
            shutil.copyfile("/home/datrus/gen_bundle/dist/bundle.js",path)
            res=get_model("theme.file").search([["theme_id","=",theme_id],["name","=",obj.name]])
            if not res:
                get_model("theme.file").create({"theme_id":theme_id,"name":obj.name,"file":fname2})
            else:
                file_id=res[0]
                get_model("theme.file").write([file_id],{"file":fname2})

Bundle.register()
