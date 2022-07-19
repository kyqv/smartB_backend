# Copyright (c) 2012-2015 Netforce Co. Ltd.

from netforce.model import Model, fields, get_model
from netforce import utils
from netforce import access
from netforce import ipc
import json
import os

class Page(Model):
    _name = "page.layout"
    _string = "Page"
    _audit_log = True
    _history=True
    _key=["path"]
    _fields = {
        "name": fields.Char("Page Title",required=True),
        "path": fields.Char("Page Code",required=True),
        "layout": fields.Text("Layout"),
        "code": fields.Text("Code"),
        "code_trans": fields.Text("Code (Transpiled)"),
        "website_id": fields.Many2One("website","Website"),
        "type": fields.Selection([["report","Report (DEPRECATED)"],["web","Web"],["mobile","Mobile"],["email","Email"],["text","Text"],["html","HTML (DEPRECATED)"]],"Page Type"),
        "sequence": fields.Integer("Sequence"),
        "show_menu": fields.Boolean("Show In Menu"),
        "model_id": fields.Many2One("model","Model"),
        "preview_type": fields.Selection([["web","Web"],["pdf","PDF"]],"Preview Type"),
        "group_id": fields.Many2One("page.group","Page Group",search=True),
        "state": fields.Selection([["draft","Draft"],["done","Completed"]],"Status"),
        "styles": fields.Text("Styles",function="get_styles"),
    }
    _order="type,sequence,name"
    _defaults={
        "state": "draft",
    }

    def create(self, *a, **kw):
        new_id = super().create(*a, **kw)
        ipc.send_signal("clear_ui_params_cache")
        return new_id

    def write(self, ids, vals, **kw):
        if not "state" in vals:
            for obj in self.browse(ids):
                if obj.state=="done":
                    raise Exception("Invalid page status")
        res = super().write(ids, vals, **kw)
        ipc.send_signal("clear_ui_params_cache")

    def delete(self, ids, **kw):
        for obj in self.browse(ids):
            if obj.state=="done":
                raise Exception("Invalid page status")
        res = super().delete(ids, **kw)
        ipc.send_signal("clear_ui_params_cache")

    def components_to_json(self,context={}):
        access.set_active_user(1)
        data={}
        for obj in self.search_browse([["website_id","=",None]]):
            try:
                layout=json.loads(obj.layout)
            except:
                layout=None
            data[obj.path]={
                "layout": layout,
                "code": obj.code,
            }
        return data

    def transpile(self,ids,context={}):
        print("transpile",ids)
        obj=self.browse(ids[0])
        if not obj.code:
            raise Exception("Missing code")
        path="/home/nf/babel/orig_code.js"
        f=open(path,"w")
        f.write(obj.code)
        f.close()
        code_trans=os.popen("cd /home/nf/babel; npx babel %s"%path).read()
        print("=> code_trans")
        print(code_trans)
        obj.write({"code_trans":code_trans})

    def set_done(self,ids,context={}):
        self.write(ids,{"state":"done"})

    def get_styles(self,ids,context={}):
        res=get_model("page.style").search([])
        if res:
            style_id=res[0]
            style=get_model("page.style").browse(style_id)
            styles=style.styles
        else:
            styles=None
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=styles
        return vals

Page.register()
