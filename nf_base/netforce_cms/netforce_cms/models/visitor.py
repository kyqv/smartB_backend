from netforce.model import Model, fields, get_model

class Visitor(Model):
    _name = "visitor"
    _string = "Visitor"
    _name_field="id_no"
    _fields = {
        "id_no": fields.Char("Visitor ID",required=True),
        "name": fields.Char("Name"),
        "user_agent": fields.Char("User Agent",size=4096),
        "create_time": fields.DateTime("Create Time",readonly=True),
        "sessions": fields.One2Many("visitor.session","visitor_id","Sessions"),
        "actions": fields.One2Many("visitor.action","visitor_id","Actions"),
        "num_sessions": fields.Integer("Num Sessions",function="get_num_sessions"),
        "num_actions": fields.Integer("Num Actions",function="get_num_actions"),
        "is_bot": fields.Boolean("Bot",function="get_bot"),
        "is_paid": fields.Boolean("Paid",function="get_paid"),
    }
    _order="id desc"

    def name_get(self,ids,**kw):
        vals=[]
        for obj in self.browse(ids):
            name=obj.id_no
            if obj.name:
                name=obj.name
            vals.append((obj.id,name))
        return vals
    
    def get_num_sessions(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.sessions)
        return vals

    def get_num_actions(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=len(obj.actions)
        return vals

    def get_bot(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            bot=False
            if obj.user_agent:
                if obj.user_agent.find("Bot")!=-1:
                    bot=True
                elif obj.user_agent.find("spider")!=-1:
                    bot=True
            vals[obj.id]=bot
        return vals

    def get_paid(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            paid=False
            for action in obj.actions:
                if action.location.find("gclid")!=-1:
                    paid=True
            vals[obj.id]=paid
        return vals

Visitor.register()
