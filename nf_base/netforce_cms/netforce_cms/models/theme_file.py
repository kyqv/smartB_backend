from netforce.model import Model,fields,get_model
from netforce import utils
import os
from netforce import database
import shutil
from netforce import config

class File(Model):
    _name="theme.file"
    _string="Static File"
    _fields={
        "theme_id": fields.Many2One("theme","Theme",required=True,on_delete="cascade"),
        "name": fields.Char("File Name",required=True,search=True),
        "file": fields.File("File"),
        "body": fields.Text("Text Data"),
        "size": fields.Integer("Size",function="get_size"),
        "compress": fields.Boolean("Compress"),
        "compress_file": fields.File("Compressed File"),
        "compress_size": fields.Integer("Compressed Size",function="get_compress_size"),
        "max_age": fields.Integer("Max Age"),
    }
    _order="name"

    def create(self,vals,*args,**kw):
        new_id=super().create(vals,*args,**kw)
        self.export_files([new_id])
        return new_id

    def write(self,ids,vals,*args,**kw):
        super().write(ids,vals,*args,**kw)
        self.export_files(ids)

    def export_files(self,ids,context={}):
        print("export_files",ids)
        for obj in self.browse(ids):
            print("exporting file %s ..."%obj.name)
            for website in obj.theme_id.websites:
                dbname = database.get_active_db()
                static_dir=config.get("static_dir") or "static"
                out_path = os.path.join(static_dir, "db", dbname, "website", website.domain, obj.name)
                dir_path=os.path.split(out_path)[0]
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                print("export_file",out_path)
                if obj.body:
                    f=open(out_path,"wb")
                    f.write(obj.body.encode("utf-8"))
                    f.close()
                elif obj.file:
                    in_path=utils.get_file_path(obj.file)
                    shutil.copyfile(in_path,out_path)

    def get_size(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            s=None
            if obj.body:
                s=len(obj.body)
            elif obj.file:
                path=utils.get_file_path(obj.file)
                if os.path.exists(path):
                    s=os.path.getsize(path)
            vals[obj.id]=s
        return vals

    def merge_file(self,vals,context={}):
        res=self.search([["theme_id","=",vals["theme_id"]],["name","=",vals["name"]]],context=context)
        if res:
            obj_id=res[0]
            self.write([obj_id],vals,context=context)
        else:
            obj_id=self.create(vals,context=context)
        return obj_id

    def do_compress(self,ids,context={}):
        print("ThemeFile.do_compress",ids)
        for obj in self.browse(ids):
            if obj.compress:
                print("compressing %s"%obj.name)
                if obj.file:
                    path=utils.get_file_path(obj.file)
                    cpath=path+".gz"
                    os.system("gzip -9 -f < %s > %s"%(path,cpath))
                    obj.write({"compress_file":cpath})

    def get_compress_size(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            s=None
            if obj.compress_file:
                path=utils.get_file_path(obj.compress_file)
                if os.path.exists(path):
                    s=os.path.getsize(path)
            vals[obj.id]=s
        return vals

File.register()
