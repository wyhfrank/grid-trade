import traceback

class MyException(Exception):
    pass


def raise_my_error():
    raise MyException('abc')

def test_stacktrace():
    try:
        raise_my_error()
    except Exception as e:
        # print(e)
        s = traceback.format_exc()
        print(s)


test_stacktrace()
