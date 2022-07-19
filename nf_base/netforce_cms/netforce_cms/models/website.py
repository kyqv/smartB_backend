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
from netforce import utils
try:
    import boto3
except:
    pass
import mimetypes
import os
import base64

class Website(Model):
    _name = "website"
    _string = "Website"
    _fields = {
        "name": fields.Char("Website Name"),
        "domain": fields.Char("Domain"),
        "theme_id": fields.Many2One("theme","Theme"),
        "aws_bucket": fields.Char("S3 Bucket Name"),
        "aws_key_id": fields.Char("AWS Key ID"),
        "aws_key_secret": fields.Char("AWS Key Secret"),
    }
    _order="name"
    _defaults = {
        "state": "active",
    }

    def upload_website(self,ids,context={}):
        print("upload_website",ids)
        obj=self.browse(ids[0])
        theme=obj.theme_id
        if not theme:
            raise Exception("Missing theme")
        session = boto3.Session(
            aws_access_key_id=obj.aws_key_id,
            aws_secret_access_key=obj.aws_key_secret,
        )
        s3=session.client("s3",region_name="ap-southeast-1")
        if not obj.aws_bucket:
            raise Exception("Missing bucket name")
        for tf in obj.theme_id.files:
            print("Uploading %s..."%tf.name)
            if tf.file:
                path=utils.get_file_path(tf.file)
                mime_type=mimetypes.guess_type(path)
                args={"ContentType":mime_type[0]}
                if tf.max_age:
                    args["CacheControl"]="max-age=%s"%tf.max_age
                if tf.compress_file:
                    cpath=utils.get_file_path(tf.compress_file)
                    args["ContentEncoding"]="gzip"
                    s3.upload_file(cpath,obj.aws_bucket,tf.name,ExtraArgs=args)
                else:
                    s3.upload_file(path,obj.aws_bucket,tf.name,ExtraArgs=args)

Website.register()
