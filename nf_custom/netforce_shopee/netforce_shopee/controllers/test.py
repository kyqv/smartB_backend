import configparser


def load_map(filename="./mapping.conf"):
    mapping = {}
    if filename:
        test = open(filename).read()  # XXX: test if have permissions to read
        parser = configparser.ConfigParser()
        parser.read(filename)
        if parser.has_section("mapping"):
            for k, v in parser.items("mapping"):
                mapping[k] = v
    else:
        print("No configuration file found")
    return mapping


mapping = load_map()
print(mapping)
shop_id = 282956279
dbs = []
for k,v in mapping.items():
    print("%s: %s"%(k,v.split(" ")))
    if str(shop_id) in v:
        dbs.append(k)
print(dbs)
