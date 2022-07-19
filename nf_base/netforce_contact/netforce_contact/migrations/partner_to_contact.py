from netforce.model import get_model
from netforce import migration
from netforce import database

class Migration(migration.Migration):
    _name="contact.partner_to_contact"
    _version="2.13.0"
    _when="before_update"

    def migrate(self):
        db=database.get_connection()
        db.execute("DROP TABLE IF EXISTS contact CASCADE")
        db.execute("CREATE TABLE contact AS SELECT * FROM partner")
        db.execute("ALTER TABLE contact ADD PRIMARY KEY (id)")
        db.execute("CREATE SEQUENCE contact_id_seq")
        db.execute("ALTER TABLE contact ALTER id SET DEFAULT nextval('contact_id_seq')")

        db.execute("DROP TABLE IF EXISTS contact_categ CASCADE")
        db.execute("CREATE TABLE contact_categ AS SELECT * FROM partner_categ")
        db.execute("ALTER TABLE contact_categ ADD PRIMARY KEY (id);")
        db.execute("CREATE SEQUENCE contact_categ_id_seq")
        db.execute("ALTER TABLE contact_categ ALTER id SET DEFAULT nextval('contact_categ_id_seq')")

Migration.register()
