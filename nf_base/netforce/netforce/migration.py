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

from netforce.model import get_model
from netforce.utils import compare_version, get_db_version
from netforce.database import get_connection
from netforce.access import set_active_user, set_active_company

_migrations = []


class Migration(object):
    _name = None
    _version = None
    _max_version = None

    @classmethod
    def register(cls):
        if not cls._name:
            raise Exception("Missing name in migration: %s" % cls.__name__)
        _migrations.append(cls)

    def migrate(self):
        pass


def apply_migrations(from_version):
    to_version = get_db_version()
    print("Applying migrations from version %s to %s..." % (from_version, to_version))
    for mig_cls in sorted(_migrations, key=lambda m: (m._version, m._name)):
        if compare_version(mig_cls._version, from_version) <= 0:
            continue
        if mig_cls._max_version and compare_version(to_version, mig_cls._max_version) > 0:
            raise Exception(
                "Can not apply migration '%s', maximum version that can apply this migration is %s" % (mig._name, mig._max_version))
        mig = mig_cls()
        print("Applying migration %s..." % mig._name)
        set_active_user(1)
        set_active_company(None)
        mig.migrate()
