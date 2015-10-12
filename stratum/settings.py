import os.path


def setup():
    '''
        This will import modules config_default and config and move their variables
        into current module (variables in config have higher priority than config_default).
        Thanks to this, you can import settings anywhere in the application and you'll get
        actual application settings.
        
        This config is related to server side. You don't need config.py if you
        want to use client part only.
    '''

    def read_values_file(cfg):
        values = []
        for line in cfg:
            if not line.count('#') and line.count('='):
                cfgvars = line.split('=')
                varname = cfgvars[0].strip()
                value = cfgvars[1].strip()
                if value in ('True','False'):
                    value = value == 'True'
                elif not value.count('"'):
                    value = int(value)
                else:
                    value = value.replace('"','')
                yield (varname, value)

    def read_values(cfg):
        for varname in cfg.__dict__.keys():
            if varname.startswith('__'):
                continue
            value = getattr(cfg, varname)
            yield (varname, value)

    import config_default
    
    if os.path.isfile('eth-proxy.conf'):
        config = open('eth-proxy.conf','r').readlines()
    else:
        # Custom config not presented, but we can still use defaults
        config = None
            
    import sys
    module = sys.modules[__name__]
    
    for name,value in read_values(config_default):
        module.__dict__[name] = value

    changes = {}
    if config:
        for name,value in read_values_file(config):
            if value != module.__dict__.get(name, None):
                if name=="DEBUG" and value:
                    changes["LOGLEVEL"] = "DEBUG"
                    module.__dict__["LOGLEVEL"] = "DEBUG"
                if name=="LOG_TO_FILE" and value:
                    changes["LOGFILE"] = "proxy.log"
                    module.__dict__["LOGFILE"] = "proxy.log"
                changes[name] = value
            module.__dict__[name] = value

    if module.__dict__['DEBUG'] and changes:
        print "----------------"
        print "Custom settings:"
        for k, v in changes.items():
            if 'passw' in k.lower():
                print k, ": ********"
            else:
                print k, ":", v
        print "----------------"

setup()
