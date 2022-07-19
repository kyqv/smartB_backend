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


class Rule(Model):
    _name = "wkf.rule"
    _string = "Workflow Rule"
    _name_field = "description"
    _fields = {
        "trigger_model_id": fields.Many2One("model", "Trigger Model", required=True, search=True),
        "trigger_event": fields.Char("Trigger Event", required=True, search=True),
        "condition_method": fields.Char("Condition Method"),
        "condition_args": fields.Text("Condition Arguments"),
        "action_model_id": fields.Many2One("model", "Action Model", search=True),
        "action_method": fields.Char("Action Method"),
        "action_args": fields.Text("Action Arguments"),
        "description": fields.Text("Rule Description", search=True),
        "comments": fields.One2Many("message", "related_id", "Comments"),
        "state": fields.Selection([["active", "Active"], ["inactive", "Inactive"]], "Status", required=True, search=True),
        "error": fields.Text("Error Message"),
        "tasks": fields.One2Many("bg.task","wkf_rule_id","Task Queue"), # XXX: deprecated
        "sequence": fields.Integer("Sequence"),
        "action_stop": fields.Boolean("Stop Rule Execution"),
        #"active": fields.Boolean("Active"),
    }
    _order = "trigger_model_id.name,trigger_event,sequence,action_model_id.name,action_method"
    _defaults = {
        "state": "active",
        #"active": True,
    }

Rule.register()
