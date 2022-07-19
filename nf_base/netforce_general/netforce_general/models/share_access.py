# Copyright (c) 2012-2015 Netforce Co. Ltd.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

from netforce.model import Model, fields
from netforce import access


class ShareAccess(Model):
    _name = "share.access"
    _string = "Sharing Setting"
    _order = "model_id"
    _fields = {
        "model_id": fields.Many2One("model", "Model", required=True, search=True),
        "default_access": fields.Selection([["private", "Private"], ["public_ro", "Public Read Only"], ["public_rw", "Public Read/Write"], ["custom", "Custom Filter"]], "Default Access", required=True, search=True),
        "grant_parent": fields.Boolean("Grant Access Using Hierarchies"),
        "description": fields.Text("Description", search=True),
        "condition": fields.Text("Filter Expression"),
        "filter_type": fields.Selection([["rw", "Read/Write"], ["w", "Write Only"]], "Filter Type"),
        "profile_id": fields.Many2One("profile", "Profile", on_delete="cascade"),  # XXX: not needed any more
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "active": fields.Boolean("Active"),
        "select_profile": fields.Selection([["all", "All Profiles"], ["include", "Include List"], ["exclude", "Exclude List"]], "Apply To Profile"),
        "profiles": fields.Many2Many("profile", "Include Profiles", "m2m_share_profile", "share_id", "profile_id"),
        "excl_profiles": fields.Many2Many("profile", "Exclude Profiles", "m2m_share_excl_profile", "share_id", "profile_id"),
        "profile_names": fields.Text("Apply To Profiles", function="_get_profile_names"),
    }
    _defaults = {
        "active": True,
    }
    _order = "model_id,description"

    def _get_profile_names(self, ids, context={}):
        vals = {}
        for obj in self.browse(ids):
            if obj.select_profile == "all":
                names = "All"
            elif obj.select_profile == "include":
                names = ",".join([p.code or p.name for p in obj.profiles])
            elif obj.select_profile == "exclude":
                names = "All except " + ",".join([p.code or p.name for p in obj.excl_profiles])
            else:
                names = "ERROR"
            vals[obj.id] = names
        return vals

ShareAccess.register()
