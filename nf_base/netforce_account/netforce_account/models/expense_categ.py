from netforce.model import Model, fields, get_model
from netforce import access

class ExpenseCateg(Model):
    _name="expense.categ"
    _string="Expense Category"
    _fields={
        "name": fields.Char("Category Name",required=True),
        "description": fields.Text("Category Description"),
    }
    _order="name"

ExpenseCateg.register()
