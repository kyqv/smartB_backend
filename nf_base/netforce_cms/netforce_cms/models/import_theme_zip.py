from netforce.model import Model,fields,get_model
from netforce import utils
from netforce import tasks
from netforce import database
import zipfile
import base64
import os
import json

class ImportZip(Model):
    _name="import.theme.zip"
    _transient=True
    _fields={
        "file": fields.File("ZIP File",required=True),
    }

    def import_zip(self,ids,context={}):
        print("import_zip",ids)
        obj=self.browse(ids[0])
        get_model("theme").import_zip(obj.file)

ImportZip.register()
