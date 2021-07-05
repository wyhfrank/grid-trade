import functools

class Person:
    precision = 2
    def __init__(self) -> None:
        self.val1 = 0.123456
        self.val2 = 0.654321
    @staticmethod
    def format_float(obj, field_name):
        return str(round(getattr(obj, field_name), obj.precision))

    @staticmethod
    def get_formatter(field_name):
        def format_float(obj):
            return str(round(getattr(obj, field_name), obj.precision))
        return property(format_float)

    @classmethod
    def add_new_field(cls):
        for field_name in ['val1', 'val2']:
            # setattr(cls, field_name+'_s', property(lambda obj: str(round(getattr(obj, field_name), obj.precision))))
            setattr(cls, field_name+'_s', cls.get_formatter(field_name=field_name))


def test_add_class_property():
    p = Person()
    print(p.val1)

    Person.add_new_field()
    # field_name = 'val'
    # setattr(Person, field_name+'_s', property(lambda obj: str(round(obj.val, obj.precision))))

    print(p.val1_s)
    print(p.val2_s)


def my_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def test_decorator():
    @my_decorator
    def adder(a, b):
        return a + b

    print(adder.__name__)
    print(adder(1, 2))
    

def decorate_formatter(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"args:", args)
        print(f"kwargs:", kwargs)
        return func(*args, **kwargs)
    return wrapper    

# @decorate_formatter
def format_float(obj, field_name):
    return str(round(getattr(obj, field_name), obj.precision))


def get_formatter(field_name):
    def format_float(obj):
        return str(round(getattr(obj, field_name), obj.precision))
    return format_float


def test_format_wrapper():
    fn = 'val1'
    setattr(Person, fn + '_s', get_formatter(fn))
    # Person.val1_s = get_formatter(fn)
    p = Person()
    print(p.val1_s())

if __name__ == "__main__":
    test_add_class_property()
    # test_format_wrapper()
