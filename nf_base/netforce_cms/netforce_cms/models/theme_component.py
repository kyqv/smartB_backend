from netforce.model import Model,fields,get_model
from netforce import database
import requests
import os
import re
from netforce import config
from datetime import *
import time

class Component(Model):
    _name="theme.component"
    _string="Component"
    _fields={
        "theme_id": fields.Many2One("theme","Theme",required=True,on_delete="cascade"),
        "name": fields.Char("Component Name",required=True,search=True),
        "body": fields.Text("Code (JSX)",required=True,search=True),
        "server_render": fields.Boolean("Server Rendering"),
        "type": fields.Selection([["server","Server"],["browser","Browser"],["mobile","Mobile"]],"Type",store=False,function_search="search_type"),
    }
    _order="name"

    def create(self,vals,*args,context={},**kw):
        new_id=super().create(vals,*args,**kw)
        if not context.get("no_export"):
            self.export_components([new_id])
        return new_id

    def write(self,ids,vals,*args,context={},**kw):
        super().write(ids,vals,*args,**kw)
        if not context.get("no_export"):
            self.export_components(ids)

    def export_components(self,ids,context={}):
        for obj in self.browse(ids):
            for site in obj.theme_id.websites:
                dbname=database.get_active_db()
                domain=site.domain
                if not domain:
                    continue
                component_path=config.get("component_path") or "./db_components"
                dir_path=component_path+"/"+dbname+"/"+domain
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                comp_path=dir_path+"/"+obj.name+".jsx"
                src=obj.body or ""
                open(comp_path,"wb").write(src.encode("utf-8"))

    def sync_components(self,ids,context={}):
        for obj in self.browse(ids,context={"no_export":True}):
            for site in obj.theme_id.websites:
                dbname=database.get_active_db()
                domain=site.domain
                if not domain:
                    continue
                component_path=config.get("component_path") or "./db_components"
                dir_path=component_path+"/"+dbname+"/"+domain
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                comp_path=dir_path+"/"+obj.name+".jsx"
                copy_from="db"
                if os.path.exists(comp_path):
                    mtime=os.path.getmtime(comp_path)
                    t=datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    if t>obj.write_time:
                        copy_from="file"
                if copy_from=="db":
                    src=obj.body or ""
                    open(comp_path,"wb").write(src.encode("utf-8"))
                elif copy_from=="file":
                    src=open(comp_path,"rb").read().decode("utf-8")
                    obj.write({"body":src})

    def search_type(self,clause,context={}):
        type=clause[2]
        ids=[]
        for obj in self.search_browse([]):
            name=obj.name
            if type=="server":
                if not name.startswith("_"):
                    ids.append(obj.id)
            elif type=="browser":
                if name.startswith("_") and not name.startswith("__"):
                    ids.append(obj.id)
            elif type=="mobile":
                if name.startswith("__"):
                    ids.append(obj.id)
        return ["id","in",ids]

Component.register()
