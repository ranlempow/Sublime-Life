# -*- coding: UTF-8 -*-

import sys
import inspect
import types

class TopLevel:
    pass
    
class Type(type):
    def __init__(cls, name, bases, namespace):
        pass
        
    def __repr__(cls):
        return "<class %s>" % cls.__name__
        
    # for pdoc
    def __subclasses__():
        return ()
        
class _Method:
    def __init__(self, name, value, binds, specs, module, super=None):
        """
        @name: str
        @bind: class
        @module: str
        @super: _Method
        """
        
        self.name = name
        self.value = value
        
        self.binds = []
        self.specs = []
        self.combination = []
        self.addCombination(binds, specs)
        
        self.module = module
        self.super = super
        if hasattr(value, '__doc__') and value.__doc__:
            lines = value.__doc__.split('\n')
            if lines[0].strip():
                self.shortdesc = lines[0]
            elif len(lines) > 0:
                self.shortdesc = lines[1]
            else:
                self.shortdesc = lines[0]
        else:
            self.shortdesc = ''
        
    def addCombination(self, target=None, specs=None):
        import itertools
        target = target if target is not None else [_]
        specs = specs if specs is not None else [True]
        self.binds.extend([ e for e in target if e not in self.binds])
        self.specs.extend([ e for e in specs if e not in self.specs])
        self.combination.extend([ e for e in itertools.product(target, specs) if e not in self.combination])
    
    # def same(self, other):
    #     return self.func == other.func  
    # def same(self, other):
    #     return self.name == other.name and self.bind == other.bind
        
    def __repr__(self):
        return '<Method {} {}>'.format(self.name, self.module)
        

_debug_mixin_observer = {}
def _clear_debug():
    for v in _debug_mixin_observer.values():
        del v[:]
        
_CreateOnlyFromMixin = object()

def mixinTo(target=None, specs=None, name=None, module=None):
    def wrap(func):
        match = list(filter(lambda m: m.value == func, _._methods))
        if len(match) == 0:
            method = _Method(
                    name or func.__name__,
                    func,
                    target,
                    specs if specs is not _CreateOnlyFromMixin else None,
                    module)
            _._methods.append(method)
        else:
            method = match[0]
            if specs is not _CreateOnlyFromMixin:
                method.addCombination(target, specs)
        return func if specs is not _CreateOnlyFromMixin else method
    return wrap
    
    
def mixin(target, source=None, inherit=None, chain=True, module=None, *, _debug=False):
    if source is None:
        source = target
        target = (_,) 
    if not isinstance(target, tuple):
        target = (target,)
    
    sourceIsLocalized = isinstance(source, types.ModuleType) and hasattr(source, 'mixin')
    pairs = []
    if isinstance(source, types.FunctionType):
        pairs.append((source.__name__, source))
    else:
        if not hasattr(source, 'items'):
            source = source.__dict__
        pairs += list(source.items())
    
    
    methods = []
    for name, value in pairs:
        if name[0] == '_' or name == 'setup':
            continue
        
        # 'escape_name' must be remove for example like 'escape_name_boo' -> '_boo'
        name = name.replace('escape_name', '')
        
        method = mixinTo(target, _CreateOnlyFromMixin, name=name, module=module)(value)
        methods.append(method)
        # debug recording
        if _debug:
            for bind in method.binds:
                _debug_mixin_observer.setdefault(bind, []).append(method)
            
    for method in methods:
        for bi, bind in enumerate(method.binds):
            if isinstance(bind, str):
                if hasattr(_, bind):
                    bind = method.binds[bi] = getattr(_, bind)
                else:
                    # skip string target that is not in TopLevel
                    continue
                        
            # inject to bind target
            value = method.value
            if hasattr(bind, '_mixfix'):
                value = bind._mixfix(value)
            setattr(bind, method.name, value)
            
            # inject to module global
            if bind is _:
                for inject in _._injecteds.keys():
                    setattr(inject, method.name, method.value)
                    
                    
def methods(mixins=None, catalog=None, includeHidden=False, functionOnly=False):
    """
    abc
    """
    if mixins and not isinstance(mixins, list):
        mixins = [mixins]
    if catalog and not isinstance(catalog, list):
        catalog = [catalog]

    groupName = {}
    for m in _._methods:
        if mixins and m.bind not in mixins:
            continue
        if catalog and m.module not in catalog:
            continue
        if functionOnly and not isinstance(m.values, types.FunctionType):
            continue
            
        groupName.setdefault((m.name, m.module, m.shortdesc), []).append(m)

    groupModule = {}
    for (name, module, shortdesc), _methods in groupName.items():
        groupModule.setdefault(module, []).append( ((name, module, shortdesc), _methods) )
       
    for module, contains in sorted(groupModule.items(), key=lambda v: v[0]):
        print('## ' + module)
        for (name, module, shortdesc), _methods in sorted(contains, key=lambda v: v[0][0]):
            print('    {:20s} {:12s} {}'.format(name, module, shortdesc))
            

def types():
    types = set()
    for t in _.__dict__.values():
        if isinstance(t, Type):
            types.add(t)
    t = list(t)
    return t
    
    
def require(path, *, _debug=False):
    import importlib
    import copy
    try:
        module = importlib.import_module(path + '_', package=None)
    except ImportError:
        module = None
    if not module:
        module = importlib.import_module(path, package=None)
        
    if _debug:
        _clear_debug()
    
    if not hasattr(module, '_already_setup'):
        if hasattr(module, 'setup'):
            oldTopLevel = copy.copy(_)
            oldTopLevel.mixin = (lambda mod: lambda *args: mixin(*args, module=mod, _debug=_debug))(module.__name__)
            #print('setup', module)
            module.setup(oldTopLevel)
        else:
            #print('autosetup', module)
            mixin(module, module=module.__name__, _debug=_debug)
        module._already_setup = True
    return module
    
    
def localize(*members):
    frm = inspect.stack()[1]
    mod = inspect.getmodule(frm[0])
    
    if len(members) == 0:
        _._injecteds[mod] = True
    for name, method in _.__dict__.items():
        if name[0] != '_' and len(members) == 0 or name in members:
            setattr(mod, name, method)
    
    
# def describe(doc=None):
    # def describer(func):
        # func.__doc__ = doc
        # return func
    # return describer
    
    
_ = TopLevel()
_._injecteds = {}
_._methods = []


mixin({
    'TopLevel': TopLevel,
    'Type': Type,
    'mixinTo': mixinTo,
    'mixin': mixin,
    'require': require,
    'localize': localize,
    'methods': methods,
}, module='core')

