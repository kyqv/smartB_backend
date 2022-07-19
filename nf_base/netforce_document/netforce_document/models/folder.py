from netforce.model import Model,fields,get_model
from netforce import access
from netforce import database

class Folder(Model):
    _name="folder"
    _string="Folder"
    _audit_log=True
    _fields={
        "name": fields.Char("Folder Name",required=True,search=True,size=16384),
        "docs": fields.One2Many("document","folder_id","Documents"),
        "num_files": fields.Integer("# Documents",function="get_num_files"),
        "parent_id": fields.Many2One("folder","Parent",on_delete="cascade"),
        "sub_folders": fields.One2Many("folder","parent_id","Sub Folders"),
        "contact_id": fields.Many2One("contact","Contact",search=True),
        "related_id": fields.Reference([["jc.job","Job"]],"Related To",search=True),
        "user_id": fields.Many2One("base.user","Created By",search=True),
        "company_id": fields.Many2One("company","Company",required=True),
    }
    _order="name"
    _defaults={
        "user_id": lambda *a: access.get_active_user(),
        "company_id": lambda *a: access.get_active_company(),
    }
    _constraints = ["_check_cycle"]

    def get_num_files(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.docs)
        return vals

Folder.register()
