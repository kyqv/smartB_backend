from netforce.model import Model, fields, get_model
from netforce import database
from netforce import utils


class RecordAccess(Model):
    _name = "record.access"
    _fields = {
        "model": fields.Char("Model",required=True),
        "record_id": fields.Integer("Record ID",required=True),
        "email": fields.Char("Email"),
        "user_id": fields.Many2One("base.user", "User"),
        "group_id": fields.Many2One("user.group", "Group"),
        "access": fields.Selection([["r", "Read Only"], ["rw", "Read/Write"]], "Access"),
        "role_id": fields.Many2One("role", "Role"),
    }
    _defaults = {
        "access": "r",
    }

    def get_access(self,model,record_id,context={}): 
        db=database.get_connection()
        res=db.query("SELECT a.email,a.user_id,g.name AS group_name,r.name AS role_name FROM record_access a LEFT JOIN user_group g ON g.id=a.group_id LEFT JOIN role r ON r.id=a.role_id WHERE a.model=%s AND a.record_id=%s",model,record_id)
        users=[]
        for r in res:
            users.append({
                "email": r.email,
                "user_id": r.user_id,
                "group_name": r.group_name,
                "role_name": r.role_name,
            })
        res=db.query("SELECT * FROM role")
        roles=[]
        for r in res:
            roles.append({
                "id": r.id,
                "name": r.name,
            })
        res=db.query("SELECT * FROM user_group")
        groups=[]
        for r in res:
            groups.append({
                "id": r.id,
                "name": r.name,
            })
        return {
            "users": users,
            "roles": roles,
            "groups": groups,
        }

    def add_access(self,model,record_id,email,group_id,role_id,context={}):
        if not model:
            raise Exception("Missing model")
        if not record_id:
            raise Exception("Missing record ID")
        if not email and not group_id:
            raise Exception("Missing email or group")
        if email:
            email=email.strip().lower()
            if not utils.check_email_syntax(email):
                raise Exception("Invalid email")
            db=database.get_connection()
            db.execute("INSERT INTO record_access (model,record_id,email,role_id) VALUES (%s,%s,%s,%s)",model,record_id,email,role_id)
        elif group_id:
            db=database.get_connection()
            db.execute("INSERT INTO record_access (model,record_id,group_id,role_id) VALUES (%s,%s,%s,%s)",model,record_id,group_id,role_id)

    def del_access(self,model,record_id,email,context={}):
        db=database.get_connection()
        db.execute("DELETE FROM record_access WHERE model=%s AND record_id=%s AND email=%s",model,record_id,email)

    def get_read_ids(self,model,email):
        db=database.get_connection()
        res=db.query("SELECT record_id FROM record_access WHERE model=%s AND email=%s",model,email)
        ids=[r.record_id for r in res]
        return ids

    def get_write_ids(self,model,email):
        db=database.get_connection()
        res=db.query("SELECT record_id FROM record_access WHERE model=%s AND email=%s AND access='rw'",model,email)
        ids=[r.record_id for r in res]
        return ids

RecordAccess.register()
