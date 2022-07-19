from netforce.model import Model, fields, get_model
from random import choice
import string
from netforce import access

class CMSForgotPasswd(Model):
    _name = "cms.forgot.passwd"
    _transient = True
    _fields = {
        "email": fields.Char("Email", required=True),
        "key": fields.Char("Key", required=True),
    }

    def _generate_key(self, context={}):
        while 1:
            chars = string.ascii_letters + string.digits
            length = 8
            key = ''.join([choice(chars) for _ in range(length)])
            if not get_model("cms.forgot.passwd").search([["key","=",key]]):
                return key

    _defaults = {
        "key": _generate_key,
    }

CMSForgotPasswd.register()
