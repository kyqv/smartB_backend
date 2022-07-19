def translate(v): # XXX: move this
    from netforce.model import get_model
    return get_model("translation").translate(v)

class NFException(Exception):
    def __init__(self,msg,*args):
        msg_t=translate(msg) or msg
        if args:
            msg_t=msg_t%tuple(args)
        super().__init__(msg_t)
