from . import config
try:
    from jaeger_client import Config
except:
    print("failed to import jaeger")

_tracer=None
_active_span=None
_enable_tracer=False

def enable_tracer():
    global _enable_tracer
    _enable_tracer=True

def disable_tracer():
    global _enable_tracer
    _enable_tracer=False

def init_tracer():
    global _tracer
    print("T"*80)
    print("T"*80)
    print("T"*80)
    print("init_tracer")
    conf=Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
	    'local_agent': {
                'reporting_host': 'prod2.netforce.com', # XXX
            },
            "logging": True,
        },
        service_name=config.get("service_name") or "backend",
        validate=True,
    )
    _tracer=conf.initialize_tracer()
    print("=> tracer",_tracer)
    return _tracer

def get_tracer():
    return _tracer

class start_span():
    def __init__(self,name,root=False):
        self.name=name
        self.root=root

    def __enter__(self):
        global _active_span
        if not _enable_tracer or (not self.root and not _active_span):
            self.span=None
            return
        if _tracer is None:
            init_tracer()
        self.parent_span=_active_span
        self.span=_tracer.start_span(self.name,child_of=self.parent_span)
        _active_span=self.span
        return self.span

    def __exit__(self,ex_type,ex_val,tb):
        global _active_span
        if not self.span:
            return
        self.span.finish()
        _active_span=self.parent_span
