from netforce.model import Model, fields, get_model

class SaleModif(Model):
    _name = "sale.modif"
    _transient = True
    _fields = {
        "order_id": fields.Many2One("sale.order", "Order", required=True, on_delete="cascade"),
        "contact_id": fields.Many2One("contact","Contact",function="_get_related",function_context={"path":"order_id.contact_id"}),
        "type": fields.Selection([["add_prod","Add Product"],["del_prod","Remove Product"],["change_qty","Change Qty"],["change_order","Change Header"]],"Modification Type",required=True),
        "product_id": fields.Many2One("product","Product"),
        "qty": fields.Decimal("Qty"),
        "unit_price": fields.Decimal("Unit Price"),
        "location_id": fields.Many2One("stock.location", "Location", condition=[["type", "=", "internal"]]),
        "due_date": fields.Date("Shipping Date (ETD)"),
        "delivery_date": fields.Date("Delivery Date (ETA)"),
        "ship_term_id": fields.Many2One("ship.term", "Shipping Terms"),
        "ship_port_id": fields.Many2One("ship.port", "Shipping Port"),
        "update_related": fields.Selection([["","Don't modify"],["recreate","Delete and recreate"],["update","Update (without deleting)"]],"Update Related Documents"),
    }

    def _get_contact(self,context={}):
        defaults=context.get("defaults",{})
        order_id=defaults.get("order_id")
        if not order_id:
            return
        order=get_model("sale.order").browse(order_id)
        return order.contact_id.id

    _defaults={
        "contact_id": _get_contact,
    }

    def apply_modif(self,ids,context={}):
        print("apply_modif",ids)
        obj=self.browse(ids[0])
        sale=obj.order_id
        if obj.type=="del_prod":
            prod_id=obj.product_id.id
            if not prod_id:
                raise Exception("Missing product")
            del_line_ids=[]
            for line in sale.lines:
                if line.product_id.id==prod_id:
                    del_line_ids.append(line.id)
            get_model("sale.order.line").delete(del_line_ids)
            for pick in sale.pickings:
                if pick.state not in ("pending","approved"):
                    continue
                del_line_ids=[]
                for line in pick.lines:
                    if line.product_id.id==prod_id:
                        del_line_ids.append(line.id)
                get_model("stock.move").delete(del_line_ids)
            for inv in sale.invoices:
                del_line_ids=[]
                for line in inv.lines:
                    if line.product_id.id==prod_id:
                        del_line_ids.append(line.id)
                if inv.state=="paid":
                    vals={
                        "type": "out",
                        "inv_type": "credit",
                        "contact_id": inv.contact_id,
                        "lines": [],
                        "ref": "Modif sales order %s"%sale.number,
                    }
                    for line in get_model("account.invoice.line").browse(del_line_ids):
                        line_vals={
                            "product_id": line.product_id.id,
                            "description": line.description,
                            "qty": line.qty,
                            "unit_price": line.unit_price,
                            "amount": line.amount,
                            "account_id": line.account_id.id,
                        }
                        vals["lines"].append(("create",line_vals))
                    cred_id=get_model("account.invoice").create(vals,context={"type":"out","inv_type":"credit"})
                    get_model("account.invoice").post([cred_id])
                elif inv.state=="waiting_payment":
                    inv.to_draft()
                    get_model("account.invoice.line").delete(del_line_ids)
                    inv.post()
                elif inv.state=="draft":
                    get_model("account.invoice.line").delete(del_line_ids)
            sale.function_store()
        elif obj.type=="add_prod":
            prod=obj.product_id
            vals={
                "order_id": obj.order_id.id,
                "product_id": obj.product_id.id,
                "description": obj.product_id.name,
                "qty": obj.qty,
                "uom_id": obj.product_id.uom_id.id,
                "unit_price": obj.unit_price,
                "tax_id": obj.product_id.sale_tax_id.id,
                "location_id": obj.location_id.id,
            }
            line_id=get_model("sale.order.line").create(vals)
            sale.function_store()
            """
            inv_id=None
            for inv in obj.order_id.invoices:
                if inv.state in ("waiting_payment","paid"):
                    inv_id=inv.id
                    break
            if not inv_id:
                raise Exception("Invoice not found")
            vals={
                "invoice_id": inv_id,
                "product_id": obj.product_id.id,
                "description": obj.product_id.name,
                "qty": obj.qty,
                "uom_id": obj.product_id.uom_id.id,
                "unit_price": obj.product_id.sale_price,
                "tax_id": obj.product_id.sale_tax_id.id,
                "account_id": obj.product_id.sale_account_id.id,
                "amount": obj.qty*obj.product_id.sale_price,
                "related_id": "sale.order,%s"%sale.id,
            }
            get_model("account.invoice.line").create(vals)
            get_model("account.invoice").function_store([inv_id])
            if obj.product_id.type=="stock":
                pick_id=None
                for pick in obj.order_id.pickings:
                    if pick.state in ("pending","confirmed") and pick.date[:10]==obj.due_date:
                        pick_id=pick.id
                        break
                if not pick_id:
                    vals={
                        "type": "out",
                        "date": obj.due_date+" 00:00:00",
                        "contact_id": sale.contact_id.id,
                        "ship_address_id": sale.ship_address_id.id,
                        "delivery_slot_id": obj.delivery_slot_id.id,
                        "related_id": "sale.order,%s"%sale.id,
                        "state": "pending",
                    }
                    pick_id=get_model("stock.picking").create(vals,context={"pick_type":"out"})
                if not obj.product_id.locations:
                    raise Exception("Product locations not found: %s"%obj.product_id.name)
                res = get_model("stock.location").search([["type", "=", "customer"]])
                if not res:
                    raise Exception("Customer location not found")
                cust_loc_id = res[0]
                vals={
                    "picking_id": pick_id,
                    "product_id": obj.product_id.id,
                    "qty": obj.qty,
                    "uom_id": obj.product_id.uom_id.id,
                    "location_from_id": obj.product_id.locations[0].location_id.id,
                    "location_to_id": cust_loc_id,
                    "state": "pending",
                    "related_id": "sale.order,%s"%sale.id,
                }
                get_model("stock.move").create(vals)
            """
        elif obj.type=="change_qty":
            prod_id=obj.product_id.id
            if not prod_id:
                raise Exception("Missing product")
            if not obj.qty:
                raise Exception("Missing qty")
            for line in sale.lines:
                if line.product_id.id==prod_id:
                    line.write({"qty":obj.qty})
            sale.function_store()
        elif obj.type=="change_order":
            vals={}
            if obj.due_date:
                sale.write({"due_date":obj.due_date})
            if obj.delivery_date:
                sale.write({"delivery_date":obj.delivery_date})
            if obj.ship_term_id:
                sale.write({"ship_term_id":obj.ship_term_id.id})
            if obj.ship_port_id:
                sale.write({"ship_port_id":obj.ship_port_id.id})
        else:
            raise Exception("Invalid modification type")
        if obj.update_related=="recreate":
            sale.delete_related()
            sale.to_draft()
            sale.confirm()
        elif obj.update_related=="update":
            obj.do_update_related()
        return {
            "flash": "Sales order %s modified successfully"%obj.order_id.number,
            "next": {
                "name": "sale",
                "mode": "form",
                "active_id": obj.order_id.id,
            },
        }

    def update_related(self,ids,context={}):
        pass

SaleModif.register()
