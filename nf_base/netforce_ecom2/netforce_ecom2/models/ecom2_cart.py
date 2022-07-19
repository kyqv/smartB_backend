from netforce.model import Model,fields,get_model
from netforce import access
from netforce.utils import *
from datetime import *
import time
from pprint import pprint
import json

class Cart(Model):
    _name="ecom2.cart"
    _string="Cart"
    _name_field="number"
    _audit_log=True
    #_multi_company=True
    _fields={
        "number": fields.Char("Number",required=True,search=True),
        "date": fields.DateTime("Date Created",required=True,search=True),
        "customer_id": fields.Many2One("contact","Customer",search=True),
        "lines": fields.One2Many("ecom2.cart.line","cart_id","Lines"),
        "ship_amount_details": fields.Json("Shipping Amount Details",function="get_ship_amount_details"),
        "amount_ship": fields.Decimal("Shipping Amount",function="get_amount_ship"),
        "amount_total": fields.Decimal("Total Amount",function="get_total"),
        "sale_orders": fields.One2Many("sale.order","related_id","Sales Orders"),
        "delivery_date": fields.Date("Delivery Date"),
        "ship_address_id": fields.Many2One("address","Shipping Address"),
        "bill_address_id": fields.Many2One("address","Billing Address"),
        "delivery_slot_id": fields.Many2One("delivery.slot","Peferred Delivery Slot"),
        "ship_method_id": fields.Many2One("ship.method","Shipping Method"),
        "pay_method_id": fields.Many2One("payment.method","Payment Method"),
        "logs": fields.One2Many("log","related_id","Audit Log"),
        "state": fields.Selection([["draft","Draft"],["confirmed","Confirmed"],["hold","Hold"],["canceled","Canceled"]],"Status",required=True),
        "payment_methods": fields.Json("Payment Methods",function="get_payment_methods"),
        "delivery_delay": fields.Integer("Delivery Delay (Days)",function="get_delivery_delay"),
        "delivery_slots": fields.Json("Delivery Slots",function="get_delivery_slots"),
        "delivery_slots_str": fields.Text("Delivery Slots",function="get_delivery_slots_str"),
        "date_delivery_slots": fields.Json("Date Delivery Slots",function="get_date_delivery_slots"),
        "comments": fields.Text("Comments"),
        "transaction_no": fields.Char("Payment Transaction No.",search=True),
        "currency_id": fields.Many2One("currency","Currency",required=True),
        "invoices": fields.One2Many("account.invoice","related_id","Invoices"),
        "company_id": fields.Many2One("company","Company"),
        "voucher_id": fields.Many2One("sale.voucher","Voucher"),
        "ship_addresses": fields.Json("Shipping Addresses",function="get_ship_addresses"),
        "amount_voucher": fields.Decimal("Voucher Amount",function="get_amount_voucher",function_multi=True),
        "voucher_error_message": fields.Text("Voucher Error Message",function="get_amount_voucher",function_multi=True),
        "free_ship_address": fields.Boolean("Is free Ship"),
        "pay_amount": fields.Decimal("Paid Amount"),
        "change_amount": fields.Decimal("Expected Change",function="get_change_amount"),
        "total_qty": fields.Decimal("Total Qty",function="get_total_qty"),
        "total_discount": fields.Decimal("Total Discount",function="get_total_discount"),
        "customer_discount": fields.Decimal("Customer Discount",function="_get_related",function_context={"path":"customer_id.sale_discount"}),
        "documents": fields.One2Many("document","related_id","Documents"),
        "email": fields.Char("Checkout Email"),
        "mobile": fields.Char("Checkout Mobile"),
        "bill_first_name": fields.Char("First Name"),
        "bill_last_name": fields.Char("Last Name"),
        "bill_full_name": fields.Char("Full Name"),
        "bill_company": fields.Char("Company Name"),
        "bill_phone": fields.Char("Phone Number"),
        "bill_country": fields.Char("Country"),
        "bill_address": fields.Text("Address"),
        "bill_postal_code": fields.Char("Post Code / ZIP"),
        "bill_city": fields.Char("Town / City"),
        "ship_first_name": fields.Char("First Name"),
        "ship_last_name": fields.Char("Last Name"),
        "ship_full_name": fields.Char("Full Name"),
        "ship_company": fields.Char("Company Name"),
        "ship_phone": fields.Char("Phone Number"),
        "ship_country": fields.Char("Country"),
        "ship_address": fields.Text("Address"),
        "ship_postal_code": fields.Char("Post Code / ZIP"),
        "ship_city": fields.Char("Town / City"),
    }
    _order="date desc"

    def _get_number(self, context={}):
        seq_id = get_model("sequence").find_sequence(type="ecom_cart")
        if not seq_id:
            return None
        while 1:
            num = get_model("sequence").get_next_number(seq_id, context=context)
            if not num:
                return None
            user_id = access.get_active_user()
            access.set_active_user(1)
            #company_id = access.get_active_company()
            #access.set_active_company(1) # XXX
            res = self.search([["number", "=", num]])
            access.set_active_user(user_id)
            #access.set_active_company(company_id)
            if not res:
                return num
            get_model("sequence").increment_number(seq_id, context=context)

    def _get_currency(self,context={}):
        res=get_model("company").search([]) # XXX
        if not res:
            return
        company_id=res[0]
        access.set_active_company(company_id)
        settings=get_model("settings").browse(1)
        return settings.currency_id.id

    def _get_company(self,context={}):
        res=get_model("company").search([]) # XXX
        if res:
            return res[0]

    def _get_ship_method(self,context={}):
        res=get_model("ship.method").search([],order="sequence")
        if res:
            return res[0]

    def _get_mobile(self,context={}):
        user_id=access.get_active_user()
        if not user_id:
            return
        user=get_model("base.user").browse(user_id)
        contact=user.contact_id
        if not contact:
            return
        return contact.mobile

    def _get_bill_full_name(self,context={}):
        user_id=access.get_active_user()
        if not user_id:
            return
        user=get_model("base.user").browse(user_id)
        contact=user.contact_id
        if not contact:
            return
        return contact.name

    def _get_ship_full_name(self,context={}):
        user_id=access.get_active_user()
        if not user_id:
            return
        user=get_model("base.user").browse(user_id)
        contact=user.contact_id
        if not contact:
            return
        return contact.name

    def _get_bill_address(self,context={}):
        user_id=access.get_active_user()
        if not user_id:
            return
        user=get_model("base.user").browse(user_id)
        contact=user.contact_id
        if not contact:
            return
        addr=contact.default_bill_address_id
        if not addr:
            return
        return addr.address_text

    def _get_ship_address(self,context={}):
        user_id=access.get_active_user()
        if not user_id:
            return
        user=get_model("base.user").browse(user_id)
        contact=user.contact_id
        if not contact:
            return
        addr=contact.default_ship_address_id
        if not addr:
            return
        return addr.address_text

    _defaults={
        "date": lambda *a: time.strftime("%Y-%m-%d %H:%M:%S"),
        "number": _get_number,
        "state": "draft",
        "currency_id": _get_currency,
        "company_id": _get_company,
        "ship_method_d": _get_ship_method,
        "free_ship_address":False,
        "mobile": _get_mobile,
        "bill_full_name": _get_bill_full_name,
        "ship_full_name": _get_ship_full_name,
        "bill_address": _get_bill_address,
        "ship_address": _get_ship_address,
    }

    def get_ship_amount_details(self,ids,context={}):
        print("get_ship_amount_details",ids)
        vals={}
        for obj in self.browse(ids):
            delivs=[]
            for line in obj.lines:
                date=line.delivery_date
                meth_id=line.ship_method_id.id or line.cart_id.ship_method_id.id
                addr_id=line.ship_address_id.id or line.cart_id.ship_address_id.id
                if not date or not meth_id or not addr_id:
                    continue
                delivs.append((date,meth_id,addr_id))
            delivs=list(set(delivs))
            details=[]
            for date,meth_id,addr_id in delivs:
                ctx={
                    "contact_id": obj.customer_id.id,
                    "ship_address_id": addr_id,
                }
                meth=get_model("ship.method").browse(meth_id,context=ctx)
                details.append({
                    "ship_addr_id":addr_id,
                    "date": date,
                    "ship_method_id": meth.id,
                    "ship_amount": meth.ship_amount,
                })
            vals[obj.id]=details
        return vals

    def get_amount_ship(self,ids,context={}):
        print("get_amount_ship",ids)
        vals={}
        for obj in self.browse(ids):
            ship_amt=0
            for d in obj.ship_amount_details:
                ship_amt+=d["ship_amount"] or 0
            vals[obj.id]=ship_amt
        return vals

    def get_total(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            for line in obj.lines:
                amt+=line.amount
            vals[obj.id]=amt+obj.amount_ship-obj.amount_voucher
        return vals

    def get_total_qty(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            qty=0
            for line in obj.lines:
                qty+=line.qty
            vals[obj.id]=qty
        return vals

    def get_total_discount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            amt=0
            for line in obj.lines:
                amt+=line.discount or 0
            vals[obj.id]=amt
        return vals

    def get_payment_methods(self,ids,context={}):
        res=[]
        for obj in get_model("payment.method").search_browse([]):
            res.append({
                "id": obj.id,
                "name": obj.name,
            })
        return {ids[0]: res}

    def confirm(self,ids,context={}):
        obj=self.browse(ids[0])
        user_id=context.get("user_id") # XX: remove this
        if user_id:
            user_id=int(user_id)
            user=get_model("base.user").browse(user_id)
            if user.contact_id:
                obj.write({"customer_id": user.contact_id.id})
        access.set_active_company(1) # XXX
        if not obj.customer_id:
            raise Exception("Missing contact in cart")
        contact=obj.customer_id
        vals={
            "contact_id": obj.customer_id.id,
            "ship_address_id": obj.ship_address_id.id,
            "ship_method_id": obj.ship_method_id.id,
            "bill_address_id": obj.bill_address_id.id,
            "due_date": obj.delivery_date or time.strftime("%Y-%m-%d"),
            "lines": [],
            "related_id": "ecom2.cart,%s"%obj.id,
            "delivery_slot_id": obj.delivery_slot_id.id,
            "pay_method_id": obj.pay_method_id.id,
            "other_info": obj.comments,
            "voucher_id": obj.voucher_id.id,
            "ref": obj.comments, # XXX
            "company_id": obj.company_id.id,
        }
        if not vals["ship_address_id"] and contact.addresses:
            vals["ship_address_id"]=contact.addresses[0].id
        for line in obj.lines:
            prod=line.product_id
            if line.lot_id and line.qty_avail<=0:
                raise Exception("Lot is out of stock (%s)"%prod.name)
            location_id=None
            if prod.locations:
                location_id=prod.locations[0].location_id.id
            if context.get("location_id"):
                location_id=context["location_id"]
            if not location_id:
                raise Exception("Can't find location for product %s"%prod.code)
            line_vals={
                "product_id": prod.id,
                "description": prod.description or prod.name,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "discount_amount": line.discount,
                "location_id": location_id,
                "lot_id": line.lot_id.id,
                "due_date": line.delivery_date,
                "delivery_slot_id": obj.delivery_slot_id.id,
                "ship_address_id": line.ship_address_id.id,
            }
            vals["lines"].append(("create",line_vals))
        for ship in obj.ship_amount_details:
            meth_id=ship["ship_method_id"]
            amount=ship["ship_amount"]
            meth=get_model("ship.method").browse(meth_id)
            prod=meth.product_id
            if not prod:
                raise Exception("Missing product in shipping method %s"%meth.name)
            line_vals={
                "product_id": prod.id,
                "description": prod.description,
                "qty": 1,
                "uom_id": prod.uom_id.id,
                "unit_price": amount,
            }
            vals["lines"].append(("create",line_vals))
        sale_id=get_model("sale.order").create(vals)
        sale=get_model("sale.order").browse(sale_id)
        if context.get("state")!="draft":
            sale.confirm()
            obj.write({"state":"confirmed"})
            obj.trigger("confirm_order")
        return {
            "sale_id": sale_id,
        }

    def cancel_order(self,ids,context={}):
        obj=self.browse(ids[0])
        for sale in obj.sale_orders:
            if sale.state=="voided":
                continue
            for inv in sale.invoices:
                if inv.state!="voided":
                    raise Exception("Can not cancel order %s because there are linked invoices"%sale.number)
            for pick in sale.pickings:
                if pick.state=="voided":
                    continue
                pick.void()
            sale.void()
        for inv in obj.invoices:
            if inv.state!="voided":
                raise Exception("Can not cancel cart %s because there are linked invoices"%obj.number)
        obj.write({"state":"canceled"})

    def payment_received(self,ids,context={}):
        obj=self.browse(ids[0])
        if obj.state!="waiting_payment":
            raise Exception("Cart is not waiting payment")
        res=obj.sale_orders.copy_to_invoice()
        inv_id=res["invoice_id"]
        inv=get_model("account.invoice").browse(inv_id)
        inv.write({"related_id":"ecom2.cart,%s"%obj.id})
        inv.post()
        method=obj.pay_method_id
        if not method:
            raise Exception("Missing payment method in cart %s"%obj.number)
        if not method.account_id:
            raise Exception("Missing account in payment method %s"%method.name)
        transaction_no=context.get("transaction_no")
        pmt_vals={
            "type": "in",
            "pay_type": "invoice",
            "contact_id": inv.contact_id.id,
            "account_id": method.account_id.id,
            "lines": [],
            "company_id": inv.company_id.id,
            "transaction_no": transaction_no,
        }
        line_vals={
            "invoice_id": inv_id,
            "amount": inv.amount_total,
        }
        pmt_vals["lines"].append(("create",line_vals))
        pmt_id=get_model("account.payment").create(pmt_vals,context={"type": "in"})
        get_model("account.payment").post([pmt_id])
        obj.write({"state": "paid"})
        for sale in obj.sale_orders:
            for pick in sale.pickings:
                if pick.state=="pending":
                    pick.approve()

    def to_draft(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.write({"state":"draft"})

    def add_to_cart(self,ids,product_id=None,add_qty=1,product_code=None,unit_price=None,context={}):
        cart_id=ids[0] if ids and ids[0] else None
        if not cart_id:
            vals={}
            cart_id=self.create(vals)
        company_id=access.get_active_company()
        get_model("ecom2.cart").write([cart_id],{"company_id":company_id})
        if not add_qty:
            raise Exception("Invalid qty")
        if not product_id and product_code:
            res=get_model("product").search([["code","=",product_code]])
            if not res:
                raise Exception("Product not found: %s"%product_code)
            product_id=res[0]
        res=get_model("ecom2.cart.line").search([["cart_id","=",cart_id],["product_id","=",product_id]])
        if res:
            line_id=res[0]
            line=get_model("ecom2.cart.line").browse(line_id)
            line.write({"qty": line.qty+add_qty})
        else:
            line_id=get_model("ecom2.cart.line").create({"cart_id": cart_id, "product_id": product_id, "qty": add_qty, "unit_price": unit_price})
        return {
            "cart_id": cart_id,
            "line_id": line_id,
        }

    def set_qty(self,ids,prod_id,qty,context={}):
        print("Cart.set_qty",ids,prod_id,qty)
        obj=self.browse(ids[0])
        line_id=None
        for line in obj.lines:
            if line.product_id.id==prod_id and not line.lot_id:
                line_id=line.id
                break
        if line_id:
            if qty==0:
                get_model("ecom2.cart.line").delete([line_id])
            else:
                get_model("ecom2.cart.line").write([line_id],{"qty":qty})
        else:
            if qty!=0:
                get_model("ecom2.cart.line").create({"cart_id": obj.id, "product_id": prod_id, "qty": qty})

    def set_date_qty(self,ids,due_date,prod_id,qty,context={}):
        print("Cart.set_date_qty",ids,due_date,prod_id,qty)
        obj=self.browse(ids[0])
        line_id=None
        for line in obj.lines:
            if line.delivery_date==due_date and line.product_id.id==prod_id and not line.lot_id:
                line_id=line.id
                break
        if line_id:
            if qty==0:
                get_model("ecom2.cart.line").delete([line_id])
            else:
                get_model("ecom2.cart.line").write([line_id],{"qty":qty})
        else:
            if qty!=0:
                ctx={"cart_id":obj.id,"delivery_date":due_date,"product_id":prod_id}
                get_model("ecom2.cart.line").create({"cart_id": obj.id, "product_id": prod_id, "qty": qty, "delivery_date": due_date},context=ctx)

    def add_lot(self,ids,prod_id,lot_id,context={}):
        print("Cart.add_lot",ids,prod_id,lot_id)
        obj=self.browse(ids[0])
        line_id=None
        for line in obj.lines:
            if line.product_id.id==prod_id and line.lot_id.id==lot_id:
                line_id=line.id
                break
        if line_id:
            raise Exception("Lot already added to cart")
        get_model("ecom2.cart.line").create({"cart_id": obj.id, "product_id": prod_id, "lot_id": lot_id, "qty": 1})

    def remove_lot(self,ids,prod_id,lot_id,context={}):
        obj=self.browse(ids[0])
        line_id=None
        for line in obj.lines:
            if line.product_id.id==prod_id and line.lot_id.id==lot_id:
                line_id=line.id
                break
        if not line_id:
            raise Exception("Lot not found in cart")
        get_model("ecom2.cart.line").delete([line_id])

    def set_qty_auto_select_lot(self,ids,prod_id,qty,context={}):
        print("Cart.set_qty_auto_select_lot",ids,prod_id,qty)
        obj=self.browse(ids[0])
        cur_qty=0
        for line in obj.lines:
            if line.product_id.id==prod_id:
                cur_qty+=line.qty
        diff_qty=qty-cur_qty
        if diff_qty>0:
            self.add_lots_auto_select(ids,prod_id,diff_qty,context=context)
        elif diff_qty<0:
            self.remove_lots_auto_select(ids,prod_id,-diff_qty,context=context)

    def add_lots_auto_select(self,ids,prod_id,add_qty,context={}):
        print("Cart.add_lots_auto_select",ids,prod_id,add_qty)
        obj=self.browse(ids[0])
        exclude_lot_ids=[]
        for line in obj.lines:
            if line.product_id.id==prod_id and line.lot_id:
                exclude_lot_ids.append(line.lot_id.id)
        prod=get_model("product").browse(prod_id)
        avail_qty=prod.stock_qty
        add_lot_ids=[]
        for lot in prod.stock_lots:
            if len(add_lot_ids)>=avail_qty:
                break
            if lot.id not in exclude_lot_ids:
                add_lot_ids.append(lot.id)
                if len(add_lot_ids)>=add_qty:
                    break
        print("add_lot_ids",add_lot_ids)
        for lot_id in add_lot_ids:
            get_model("ecom2.cart.line").create({
                "cart_id": obj.id,
                "product_id": prod_id,
                "lot_id": lot_id,
                "qty": 1
            })
        remain_qty=add_qty-len(add_lot_ids)
        print("remain_qty",remain_qty)
        if remain_qty>0:
            found_line=None
            for line in obj.lines:
                if line.product_id.id==prod_id and not line.lot_id:
                    found_line=line
                    break
            if found_line:
                found_line.write({"qty":found_line.qty+remain_qty})
            else:
                get_model("ecom2.cart.line").create({"cart_id": obj.id, "product_id": prod_id, "qty": remain_qty})

    def remove_lots_auto_select(self,ids,prod_id,remove_qty,context={}):
        print("Cart.remove_lots_auto_select",ids,prod_id,remove_qty)
        obj=self.browse(ids[0])
        remain_qty=remove_qty
        for line in obj.lines:
            if line.product_id.id==prod_id and not line.lot_id:
                if line.qty<=remain_qty:
                    remain_qty-=line.qty
                    line.delete()
                else:
                    line.write({"qty":line.qty-remain_qty})
                    remain_qty=0
        print("remain_qty",remain_qty)
        if remain_qty>0:
            lots=[]
            for line in obj.lines:
                if line.product_id.id==prod_id and line.lot_id:
                    d=line.lot_id.received_date or "1900-01-01"
                    lots.append((d,line.id))
            lots.sort()
            del_ids=[]
            for d,line_id in lots:
                del_ids.append(line_id)
                if len(del_ids)>=remain_qty:
                    break
            print("del_ids",del_ids)
            get_model("ecom2.cart.line").delete(del_ids)

    def get_delivery_delay(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=max(l.delivery_delay for l in obj.lines) if obj.lines else 0
        return vals

    def get_delivery_slots(self,ids,context={}):
        print("get_delivery_slots",ids)
        obj=self.browse(ids[0])
        settings=get_model("ecom2.settings").browse(1)
        max_days=settings.delivery_max_days
        if not max_days:
            return {obj.id:[]}
        min_hours=settings.delivery_min_hours or 0
        d_from=date.today()+timedelta(days=obj.delivery_delay)
        d_to=d_from+timedelta(days=max_days)
        d=d_from
        slots=[]
        for slot in get_model("delivery.slot").search_browse([]):
            slots.append([slot.id,slot.name,slot.time_from])
        slot_num_sales={}
        for sale in get_model("sale.order").search_browse([["plr_order_type","=","grocery"],["date",">=",time.strftime("%Y-%m-%d")]]):
            k=(sale.due_date,sale.delivery_slot_id.id)
            slot_num_sales.setdefault(k,0)
            slot_num_sales[k]+=1
        print("slot_num_sales",slot_num_sales)
        slot_caps={}
        for cap in get_model("delivery.slot.capacity").search_browse([]):
            k=(cap.slot_id.id,int(cap.weekday))
            slot_caps[k]=cap.capacity
        print("slot_caps",slot_caps)
        delivery_weekdays=None
        for line in obj.lines:
            prod=line.product_id
            if prod.delivery_weekdays:
                days=[int(w) for w in prod.delivery_weekdays.split(",")]
                if delivery_weekdays==None:
                    delivery_weekdays=days
                else:
                    delivery_weekdays=[d for d in delivery_weekdays if d in days]
        days=[]
        now=datetime.now()
        tomorrow=now+timedelta(days=1)
        tomorrow_seconds=0
        if settings.work_time_start and settings.work_time_end:
            today_end=datetime.strptime(date.today().strftime("%Y-%m-%d")+" "+settings.work_time_end,"%Y-%m-%d %H:%M")
            tomorrow_start=datetime.strptime(tomorrow.strftime("%Y-%m-%d")+" "+settings.work_time_start,"%Y-%m-%d %H:%M")
            if now<today_end and now.weekday()!=6:
                remain_seconds=(today_end-now).total_seconds()
            else:
                remain_seconds=0
            if remain_seconds<min_hours*3600:
                tomorrow_seconds=min_hours*3600-remain_seconds
        print("tomorrow_seconds=%s"%tomorrow_seconds)
        while d<=d_to:
            ds=d.strftime("%Y-%m-%d")
            res=get_model("hr.holiday").search([["date","=",ds]])
            if res:
                d+=timedelta(days=1)
                continue
            w=d.weekday()
            if w==6 or delivery_weekdays is not None and w not in delivery_weekdays:
                d+=timedelta(days=1)
                continue
            day_slots=[]
            for slot_id,slot_name,from_time in slots:
                t_from=datetime.strptime(ds+" "+from_time+":00","%Y-%m-%d %H:%M:%S")
                capacity=slot_caps.get((slot_id,w))
                num_sales=slot_num_sales.get((ds,slot_id),0)
                state="avail"
                if d==now.date():
                    if t_from<now or (t_from-now).total_seconds()<min_hours*3600 or tomorrow_seconds:
                        state="full"
                elif d==tomorrow.date() and tomorrow_seconds:
                    if (t_from-tomorrow_start).total_seconds()<tomorrow_seconds:
                        state="full"
                if capacity is not None and num_sales>=capacity:
                    state="full"
                day_slots.append([slot_id,slot_name,state,num_sales,capacity])
            days.append([ds,day_slots])
            d+=timedelta(days=1)
        print("days:")
        pprint(days)
        return {obj.id: days}

    def get_delivery_slots_str(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            s=""
            for d,slots in obj.delivery_slots:
                s+="- Date: %s\n"%d
                for slot_id,name,state,num_sales,capacity in slots:
                    s+="    - %s: %s (%s/%s)\n"%(name,state,num_sales,capacity or "-")
            vals[obj.id]=s
        return vals

    def get_date_delivery_slots(self,ids,context={}):
        print("get_date_delivery_slots",ids)
        obj=self.browse(ids[0])
        slots=[]
        for slot in get_model("delivery.slot").search_browse([]):
            slots.append([slot.id,slot.name])
        dates=[]
        for line in obj.lines:
            d=line.delivery_date
            if d:
                dates.append(d)
        dates=list(set(dates))
        date_slots={}
        for d in dates:
            date_slots[d]=slots # TODO: use capacity?
        return {obj.id: date_slots}

    def get_ship_addresses(self,ids,context={}):
        obj=self.browse(ids[0])
        settings=get_model("ecom2.settings").browse(1)
        contact=obj.customer_id
        addrs=[]
        if contact:
            for a in contact.addresses:
                addr_vals={
                    "id": a.id,
                    "name": a.address,
                }
                if obj.ship_method_id: # TODO: handle general case for different shipping methods per order
                    meth_id=obj.ship_method_id.id
                    ctx={"ship_address_id": a.id}
                    meth=get_model("ship.method").browse(meth_id,context=ctx)
                    addr_vals["ship_amount"]=meth.ship_amount
                else:
                    addr_vals["ship_amount"]=0
                addrs.append(addr_vals)
        for a in settings.extra_ship_addresses:
            addr_vals={
                "id": a.id,
                "name": a.address or "",
            }
            if obj.ship_method_id:
                meth_id=obj.ship_method_id.id
                ctx={"ship_address_id": a.id}
                meth=get_model("ship.method").browse(meth_id,context=ctx)
                addr_vals["ship_amount"]=meth.ship_amount
            else:
                addr_vals["ship_amount"]=0
            addrs.append(addr_vals)
        return {obj.id: addrs}

    def apply_voucher_code(self,ids,voucher_code,context={}):
        obj=self.browse(ids[0])
        res=get_model("sale.voucher").search([["code","=",voucher_code]])
        if not res:
            raise Exception("Invalid voucher code")
        voucher_id=res[0]
        obj.write({"voucher_id":voucher_id})

    def clear_voucher(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.write({"voucher_id":None})

    def get_amount_voucher(self,ids,context={}):
        print("get_amount_voucher",ids)
        vals={}
        for obj in self.browse(ids):
            voucher=obj.voucher_id
            if voucher:
                ctx={
                    "contact_id": obj.customer_id.id,
                    "amount_total": 0,
                    "products": [],
                }
                for line in obj.lines:
                    ctx["amount_total"]+=line.amount
                    ctx["products"].append({
                        "product_id": line.product_id.id,
                        "unit_price": line.unit_price,
                        "qty": line.qty,
                        "uom_id": line.uom_id.id,
                        "amount": line.amount,
                    })
                ctx["amount_total"]+=obj.amount_ship
                res=voucher.apply_voucher(context=ctx)
                disc_amount=res.get("discount_amount",0)
                error_message=res.get("error_message")
            else:
                disc_amount=0
                error_message=None
            vals[obj.id]={
                "amount_voucher": disc_amount,
                "voucher_error_message": error_message,
            }
        return vals

    def update_date_delivery(self,ids,date,vals,context={}):
        print("cart.update_date_delivery",ids,date,vals)
        obj=self.browse(ids[0])
        settings=get_model("ecom2.settings").browse(1)
        for line in obj.lines:
            if line.delivery_date==date:
                line.write(vals)
        #for a in settings.extra_ship_addresses:
            #if a.id == vals['ship_address_id']:
                #return {'free_ship':True}
        return {'free_ship':False}

    def empty_cart(self,ids,context={}):
        obj=self.browse(ids[0])
        obj.write({"lines":[("delete_all",)]})

    def check_due_dates(self,ids,context={}):
        obj=self.browse(ids[0])
        today=time.strftime("%Y-%m-%d")
        if obj.delivery_date and obj.delivery_date<today:
            raise Exception("Delivery date is in the past %s"%obj.delivery_date)
        for line in obj.lines:
            if line.delivery_date and line.delivery_date<today:
                raise Exception("Delivery date is in the past %s for product %s"%(line.delivery_date,line.product_id.name))

    def free_ship_address(self,ids,context={}):
        obj=self.browse(ids[0])
        settings=get_model("ecom2.settings").browse(1)
        data=[]
        for a in settings.extra_ship_addresses:
            if obj.ship_method_id:
                data["is_free"]=False
            else:
                data["is_free"]=True
            data.append(data)
        return {obj.id: addrs}

    def copy(self, ids, context={}):
        obj=self.browse(ids[0])
        vals={
            "customer_id": obj.customer_id.id,
            "ship_address_id": obj.ship_address_id.id,
            "ship_method_id": obj.ship_method_id.id,
            "lines": [],
        }
        for line in obj.lines:
            line_vals={
                "sequence": line.sequence,
                "product_id": line.product_id.id,
                "lot_id": line.lot_id.id,
                "unit_price": line.unit_price,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "delivery_date": line.delivery_date,
                "ship_address_id": line.ship_address_id.id,
                "packaging_id": line.packaging_id.id,
            }
            vals["lines"].append(("create",line_vals))
        new_id=self.create(vals)
        return {
            "new_id": new_id,
            "flash": "Cart copied successfully",
            "next": {
                "name": "ecom2_cart",
                "mode": "form",
                "active_id": new_id,
            }
        }

    def get_change_amount(self,ids,context={}):
        vals={}
        for obj in self.browse(ids):
            vals[obj.id]=max(0,(obj.pay_amount or 0)-(obj.amount_total or 0))
        return vals

    def set_customer(self,ids,contact_id,context={}):
        obj=self.browse(ids[0])
        obj.write({"customer_id": contact_id})

    def place_order_old(self,ids,context={}):
        obj=self.browse(ids[0])
        if not obj.email:
            raise Exception("Missing email")
        if not obj.bill_first_name:
            raise Exception("Missing billing first name")
        if not obj.bill_last_name:
            raise Exception("Missing billing last name")
        if not obj.bill_phone:
            raise Exception("Missing billing phone")
        if not obj.bill_address:
            raise Exception("Missing billing address")
        if not obj.bill_postal_code:
            raise Exception("Missing billing postal code")
        if not obj.bill_city:
            raise Exception("Missing billing city")
        ship_first_name=obj.ship_first_name or obj.bill_first_name
        ship_last_name=obj.ship_last_name or obj.bill_last_name
        ship_phone=obj.ship_phone or obj.bill_phone
        ship_address=obj.ship_address or obj.bill_address
        ship_postal_code=obj.ship_postal_code or obj.bill_postal_code
        ship_city=obj.ship_city or obj.bill_city
        res=get_model("contact").search([["email","=",obj.email]])
        if res:
            contact_id=res[0]
        else:
            vals={
                "type": "person",
                "first_name": obj.bill_first_name,
                "last_name": obj.bill_last_name,
                "email": obj.email,
            }
            contact_id=get_model("contact").create(vals)
        res=get_model("country").search([["name","=","Thailand"]]) # XXX
        if not res:
            raise Exception("Country not found: Thailand")
        country_id=res[0]
        vals={
            "contact_id": contact_id,
            "type": "billing",
            "address": obj.bill_address,
            "city": obj.bill_city,
            "postal_code": obj.bill_postal_code,
            "country_id": country_id,
            "phone": obj.bill_phone,
        }
        res=get_model("address").search([["contact_id","=",contact_id],["type","=","billing"]])
        if res:
            bill_addr_id=res[0]
            get_model("address").write([bill_addr_id],vals)
        else:
            bill_addr_id=get_model("address").create(vals)
        vals={
            "contact_id": contact_id,
            "type": "shipping",
            "address": ship_address,
            "city": ship_city,
            "postal_code": ship_postal_code,
            "country_id": country_id,
            "phone": ship_phone,
        }
        res=get_model("address").search([["contact_id","=",contact_id],["type","=","shipping"]])
        if res:
            ship_addr_id=res[0]
            get_model("address").write([ship_addr_id],vals)
        else:
            ship_addr_id=get_model("address").create(vals)
        vals={
            "contact_id": contact_id,
            "ship_address_id": ship_addr_id,
            "bill_address_id": bill_addr_id,
            "due_date": obj.delivery_date or time.strftime("%Y-%m-%d"),
            "lines": [],
            "related_id": "ecom2.cart,%s"%obj.id,
            "other_info": obj.comments,
        }
        for line in obj.lines:
            prod=line.product_id
            if line.lot_id and line.qty_avail<=0:
                raise Exception("Lot is out of stock (%s)"%prod.name)
            location_id=None
            if prod.locations:
                location_id=prod.locations[0].location_id.id
            if not location_id:
                res=get_model("stock.location").search([["type","=","internal"]])
                location_id=res[0] if res else None
            if not location_id:
                raise Exception("Can't find location for product %s"%prod.code)
            line_vals={
                "product_id": prod.id,
                "description": prod.description or prod.name,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "location_id": location_id,
                "lot_id": line.lot_id.id,
                "due_date": line.delivery_date,
                "delivery_slot_id": obj.delivery_slot_id.id,
                "ship_address_id": line.ship_address_id.id,
            }
            vals["lines"].append(("create",line_vals))
        sale_id=get_model("sale.order").create(vals)
        sale=get_model("sale.order").browse(sale_id)
        sale.confirm()
        obj.write({"state":"confirmed"})
        obj.trigger("confirm_order")
        return {
            "sale_id": sale_id,
            "sale_number": sale.number,
        }

    def place_order(self,ids,context={}):
        print("place_order",ids,context)
        obj=self.browse(ids[0])
        #if not obj.email:
        #    raise Exception("Missing email")
        if not obj.mobile:
            raise Exception("Missing mobile")
        """
        if not obj.bill_first_name:
            raise Exception("Missing billing first name")
        if not obj.bill_last_name:
            raise Exception("Missing billing last name")
        if not obj.bill_phone:
            raise Exception("Missing billing phone")
        if not obj.bill_address:
            raise Exception("Missing billing address")
        if not obj.bill_postal_code:
            raise Exception("Missing billing postal code")
        if not obj.bill_city:
            raise Exception("Missing billing city")
        """
        pay_method=context.get("pay_method")
        if pay_method:
            res=get_model("payment.method").search([["code","=",pay_method]])
            if not res:
                raise Exception("Payment method not found: %s"%pay_method)
            meth_id=res[0]
            method=get_model("payment.method").browse(meth_id)
            obj.write({"pay_method_id":meth_id})
        else:
            method=obj.pay_method_id
            if not method:
                raise NFException("Missing payment method for cart %s"%obj.number)
        pay_amt=obj.amount_total
        ctx={
            "contact_id": obj.customer_id.id,
            "related_id": "ecom2.cart,%s"%obj.id,
            "amount": pay_amt,
            "currency_id": obj.currency_id.id,
            "order_number": obj.number,
            "details": "Order %s"%obj.number,
            "return_url": context.get("return_url"),
            "error_url": context.get("error_url"),
        }
        res=method.start_payment(context=ctx)
        if not res:
            return self.copy_to_sale(ids,context=context)
            #raise NFException("Failed to start online payment for sales order %s"%obj.number)
        trans_id=res["transaction_id"]
        print("trans_id: %s"%trans_id)
        action=res.get("payment_action")
        url=action["url"] if action else None
        return {
            "next_url": url,
        }

    def copy_to_contact(self,ids,context={}):
        obj=self.browse(ids[0])
        """
        if not obj.email:
            raise Exception("Missing email")
        if not obj.bill_first_name:
            raise Exception("Missing billing first name")
        if not obj.bill_last_name:
            raise Exception("Missing billing last name")
        if not obj.bill_phone:
            raise Exception("Missing billing phone")
        if not obj.bill_address:
            raise Exception("Missing billing address")
        if not obj.bill_postal_code:
            raise Exception("Missing billing postal code")
        if not obj.bill_city:
            raise Exception("Missing billing city")
        """
        ship_first_name=obj.ship_first_name or obj.bill_first_name
        ship_last_name=obj.ship_last_name or obj.bill_last_name
        ship_phone=obj.ship_phone or obj.bill_phone
        ship_address=obj.ship_address or obj.bill_address
        ship_postal_code=obj.ship_postal_code or obj.bill_postal_code
        ship_city=obj.ship_city or obj.bill_city
        res=get_model("contact").search([["mobile","=",obj.mobile]])
        if res:
            contact_id=res[0]
        else:
            vals={
                "type": "person",
                "first_name": obj.bill_first_name,
                "last_name": obj.bill_last_name,
                "email": obj.email,
                "mobile": obj.mobile,
            }
            contact_id=get_model("contact").create(vals)
        obj.write({"customer_id":contact_id})
        if obj.bill_address:
            res=get_model("country").search([["name","=","Thailand"]]) # XXX
            if not res:
                raise Exception("Country not found: Thailand")
            country_id=res[0]
            vals={
                "contact_id": contact_id,
                "type": "billing",
                "address": obj.bill_address,
                "city": obj.bill_city,
                "postal_code": obj.bill_postal_code,
                "country_id": country_id,
                "phone": obj.bill_phone,
            }
            res=get_model("address").search([["contact_id","=",contact_id],["type","=","billing"]])
            if res:
                bill_addr_id=res[0]
                get_model("address").write([bill_addr_id],vals)
            else:
                bill_addr_id=get_model("address").create(vals)
        if ship_address:
            vals={
                "contact_id": contact_id,
                "type": "shipping",
                "address": ship_address,
                "city": ship_city,
                "postal_code": ship_postal_code,
                "country_id": country_id,
                "phone": ship_phone,
            }
            res=get_model("address").search([["contact_id","=",contact_id],["type","=","shipping"]])
            if res:
                ship_addr_id=res[0]
                get_model("address").write([ship_addr_id],vals)
            else:
                ship_addr_id=get_model("address").create(vals)

    def copy_to_sale(self,ids,context={}):
        obj=self.browse(ids[0])
        user_id=access.get_active_user()
        if not user_id:
            raise Exception("Not logged in")
        user=get_model("base.user").browse(user_id)
        if not user.contact_id:
            raise Exception("Missing user in contact")
        contact_id=user.contact_id.id
        obj.write({"customer_id":contact_id})
        obj=obj.browse()[0]
        #if not obj.customer_id:
        #    obj.copy_to_contact()
        #    obj=obj.browse()[0]
        vals={
            "contact_id": obj.customer_id.id,
            #"ship_address_id": ship_addr_id,
            #"bill_address_id": bill_addr_id,
            "due_date": obj.delivery_date or time.strftime("%Y-%m-%d"),
            "lines": [],
            "related_id": "ecom2.cart,%s"%obj.id,
            "other_info": obj.comments,
            "seller_contact_id": obj.customer_id.id,
            "tax_type": "tax_in",
        }
        for line in obj.lines:
            prod=line.product_id
            if line.lot_id and line.qty_avail<=0:
                raise Exception("Lot is out of stock (%s)"%prod.name)
            location_id=None
            if prod.locations:
                location_id=prod.locations[0].location_id.id
            if not location_id:
                res=get_model("stock.location").search([["type","=","internal"]])
                location_id=res[0] if res else None
            if not location_id:
                raise Exception("Can't find location for product %s"%prod.code)
            line_vals={
                "product_id": prod.id,
                "tax_id": prod.sale_tax_id.id,
                "description": prod.description or prod.name,
                "qty": line.qty,
                "uom_id": line.uom_id.id,
                "unit_price": line.unit_price,
                "location_id": location_id,
                "lot_id": line.lot_id.id,
                "due_date": line.delivery_date,
                "delivery_slot_id": obj.delivery_slot_id.id,
                "ship_address_id": line.ship_address_id.id,
            }
            vals["lines"].append(("create",line_vals))
        sale_id=get_model("sale.order").create(vals)
        sale=get_model("sale.order").browse(sale_id)
        if context.get("state")!="draft":
            sale.confirm()
        return {
            "sale_id": sale_id,
            "sale_number": sale.number,
        }

    def set_qtys(self,ids,qtys,context={}):
        print("Cart.set_qtys",ids,qtys)
        obj=self.browse(ids[0])
        for line in obj.lines:
            k=str(line.id) # XXX
            qty=qtys.get(k)
            if qty is not None:
                line.set_qty(qty)

Cart.register()
