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
from PIL import Image
import os.path
from netforce import database
import math


class ProductImage(Model):
    _name = "product.image"
    _fields = {
        "product_id": fields.Many2One("product", "Product", required=True, on_delete="cascade"),
        "image": fields.File("Image", required=True),
        "title": fields.Char("Title"),
        "description": fields.Text("Description"),
        "rotate_cw": fields.Boolean("Rotate Clockwise", function="_get_related", function_context={"path": "product_id.rotate_cw"}),
        "rotate_footage": fields.Char("Define Column", function="_get_related", function_context={"path": "product_id.rotate_footage"}),
        "rotate_frame": fields.Char("Define Amount of image", function="_get_related", function_context={"path": "product_id.rotate_frame"}),
        "rotate_speed": fields.Char("Define Rotating Speed", function="_get_related", function_context={"path": "product_id.rotate_speed"}),
        "rotate_height": fields.Char("Image Height", function="cal_dimension", function_multi=True),
        "rotate_width": fields.Char("Image Width", function="cal_dimension", function_multi=True),
        "master_image": fields.Char("Master image", function="cal_dimension", function_multi=True),
    }

    def cal_dimension(self, ids, context={}):
        all_vals = {}
        dbname = database.get_active_db()
        for obj in self.browse(ids):
            master_img = obj.product_id.image
            master_path = os.path.join("static/db/", dbname, "files", master_img)
            frame = int(obj.get("rotate_frame"))
            column = int(obj.get("rotate_footage"))
            row = 1
            if frame and column:
                row = frame / column
            vals = {}
            im_path = obj.image
            if im_path and frame and column:
                filename = os.path.join("static/db/", dbname, "files", im_path)
                img = Image.open(filename)
                (width, height) = img.size
                swidth = math.floor(width / column)
                sheight = math.floor(height / row)
                vals["rotate_width"] = swidth
                vals["rotate_height"] = sheight
                vals["master_image"] = master_path
                all_vals[obj.id] = vals
            else:
                print("Not enough arguments given")
        return all_vals

ProductImage.register()
