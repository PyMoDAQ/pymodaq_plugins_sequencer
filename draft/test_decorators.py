class SequencerObjectManager:

    def __init__(self):
        self.objects = []

    def register(self, obj):
        self.objects.append(obj)


sequencer_object_manager = SequencerObjectManager()


def expose(method):
    method._exposed = True
    return method


def expose_to_sequencer(manager):

    def decorator(cls):

        decorator_exposed_methods = [
            name for name in cls.__dict__
            if getattr(getattr(cls, name), "_exposed", False)
            # default False if attr _exposed not present
        ]

        if hasattr(cls, 'exposed_methods'):
            for name in decorator_exposed_methods:
                if name not in cls.exposed_methods:
                    cls.exposed_methods.append(name)
        else:
            cls.exposed_methods = decorator_exposed_methods

        original_init = cls.__init__

        def __init__(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            manager.register(self)

        cls.__init__ = __init__
        return cls

    return decorator


# class written for the sequencer
@expose_to_sequencer(sequencer_object_manager)
class ExposedClassA:

    exposed_methods = ['method_a', 'method_b']

    def __init__(self, name):
        self.name = name

    def method_a(self):
        pass

    def method_b(self):
        pass

    def method_c(self):
        pass

    def method_d(self):
        pass


# also written for the sequencer, but with method decorator approach
@expose_to_sequencer(sequencer_object_manager)
class ExposedClassB:

    def __init__(self, name):
        self.name = name

    @expose
    def method_a(self):
        pass

    def method_b(self):
        pass

    @expose
    def method_c(self):
        pass

    def method_d(self):
        pass


# also written for the sequencer, mixing both approaches because @expose is not
# compatible with @property (and possibly other decorators)
@expose_to_sequencer(sequencer_object_manager)
class ExposedClassC:

    exposed_methods = ['method_b']

    def __init__(self, name):
        self.name = name

    @expose
    def method_a(self):
        pass

    @property
    def method_b(self):
        return "something"

    def method_c(self):
        pass

    def method_d(self):
        pass


# some PyMoDAQ class to be exposed to the sequencer without modifying the class
class OriginalClass:
    
    def __init__(self, name):
        self.name = name

    def method_a(self):
        pass

    def method_b(self):
        pass

    def method_c(self):
        pass

    def method_d(self):
        pass



@expose_to_sequencer(sequencer_object_manager)
class ExposedOriginalClass(OriginalClass):
    exposed_methods = ['method_c', 'method_d']


inst1 = ExposedClassA("With Dict")
inst2 = ExposedClassB("With Decorator")
inst2 = ExposedClassC("Mixed")
inst3 = ExposedOriginalClass("Derived Class")

print([f'{o.name}: {o.exposed_methods}'
       for o in sequencer_object_manager.objects])
