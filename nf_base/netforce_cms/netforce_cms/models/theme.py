from netforce.model import Model,fields,get_model
from netforce import utils
from netforce import database
import zipfile
import os
import base64
import json
import shutil
import subprocess
from netforce import config

class Theme(Model):
    _name="theme"
    _string="Theme"
    _fields={
        "name": fields.Char("Theme Name",required=True),
        "components": fields.One2Many("theme.component","theme_id","Components"),
        "files": fields.One2Many("theme.file","theme_id","Static Files"),
        "bundles": fields.One2Many("theme.bundle","theme_id","JS Bundles"),
        "static_gens": fields.One2Many("theme.static.gen","theme_id","Static HTML Generators"),
        "websites": fields.One2Many("website","theme_id","Websites"),
        "state": fields.Selection([["active","Active"],["inactive","Inactive"]],"Status",required=True),
    }
    _order="name"
    _defaults={
        "state": "inactive",
    }

    def export_zip(self,ids,context={}):
        print("theme.export_zip",ids)
        obj=self.browse(ids[0])
        fname="%s.zip"%obj.name
        path=utils.get_file_path(fname)
        zf=zipfile.ZipFile(path,"w")
        for comp in obj.components:
            zf.writestr("components/%s.js"%comp.name,comp.body.encode("utf-8"))
        for sf in obj.files:
            if sf.file:
                path=utils.get_file_path(sf.file)
                data=open(path,"rb").read()
            else:
                data=(sf.body or "").encode("utf-8")
            zf.writestr("static/%s"%sf.name,data)
        zf.close()
        return {
            "next": {
                "type": "download",
                "filename": fname,
            }
        }

    def import_zip(self,fname,context={}):
        print("theme.import_zip",fname)
        path=utils.get_file_path(fname)
        zf = zipfile.ZipFile(path)
        if "package.json" in zf.namelist():
            data = zf.read("package.json")
            conf=json.loads(data.decode())
            print("conf",conf)
            name=conf.get("name")
            if not name:
                raise Exception("Missing theme name")
        else:
            name="New Theme"
        vals={
            "name": name,
        }
        theme_id=self.create(vals,context=context)
        print("theme_id",theme_id)
        for n in zf.namelist():
            if not n.startswith("static/"):
                continue
            print("importing static file %s ..."%n)
            if n[-1] == "/":
                continue
            fpath = n[7:]
            if fpath.find("..") != -1:
                continue
            data = zf.read(n)
            fname=os.path.basename(fpath)
            res = os.path.splitext(fname)
            root, ext = res
            rand = base64.urlsafe_b64encode(os.urandom(8)).decode()
            fname_rand = root + "," + rand + ext
            dbname=database.get_active_db()
            static_dir=config.get("static_dir") or "static"
            fpath_files = "%s/db/%s/files/%s"%(static_dir,dbname,fname_rand)
            open(fpath_files, "wb").write(data)
            vals={
                "theme_id": theme_id,
                "name": fpath,
                "file": fname_rand,
            }
            get_model("theme.file").merge_file(vals,context=context)
        for n in zf.namelist():
            if not n.startswith("components/"):
                continue
            if not n.endswith(".js"):
                continue
            print("importing component %s ..."%n)
            fname = n[11:-3]
            if fname.find("..") != -1:
                continue
            data = zf.read(n)
            vals = {
                "theme_id": theme_id,
                "name": fname,
                "body": data.decode(),
            }
            get_model("theme.component").create(vals,context=context)

    def gen_bundles(self,ids,context={}):
        obj=self.browse(ids[0])
        last_mtime=None
        for comp in obj.components:
            if not last_mtime or comp.write_time>last_mtime:
                last_mtime=comp.write_time
        print("last_mtime",last_mtime)
        bundle_ids=[]
        for bundle in obj.bundles:
            target_f=None
            for f in obj.files:
                if f.name==bundle.name:
                    target_f=f
                    break
            if not target_f or target_f.write_time<=last_mtime:
                bundle_ids.append(bundle.id)
        print("bundle_ids",bundle_ids)
        if bundle_ids:
            get_model("theme.bundle").gen_bundle(bundle_ids)

    def upload_websites(self,ids,context={}):
        print("upload_websites",ids)
        obj=self.browse(ids[0])
        for f in obj.files:
            if f.compress and not f.compress_file:
                f.do_compress()
        for website in obj.websites:
            website.upload_website()

    def set_active(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.write({"state": "active"})
        other_ids=self.search([["id","!=",obj.id]])
        self.write(other_ids,{"state":"inactive"})
        get_model("theme.component").export_active_components()

    def set_inactive(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.write({"state": "inactive"})

Theme.register()
