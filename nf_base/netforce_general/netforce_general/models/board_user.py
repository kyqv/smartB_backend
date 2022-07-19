from netforce.model import Model, fields

class Board(Model):
    _name = "board.user"
    _string = "Dashboard"
    _fields = {
        "name": fields.Char("Dashboard Name", required=True),
        "user_id": fields.Many2One("base.user","User"),
        "layout": fields.Text("Layout"),
    }
    _order="name"

Board.register()
