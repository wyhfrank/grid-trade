import sys
import traceback

class MyException(Exception):
    pass


def raise_my_error():
    raise MyException('abc')


def test_wrapper(n=5, limit=3):
    def wrapper(n):
        if n <=0:
            raise_my_error()
        else:
            n -= 1
            wrapper(n)

    try:
        wrapper(n=n)
    except Exception as e:
        # print(e)
        s = traceback.format_exc(limit=limit)
        print(s)

def test_traceback():
        s = traceback.format_exc(limit=5)
        print(s)

def test_sys_exc_info():
    # _, _, tb = sys.exc_info()
    # print(tb)
    try:
        raise_my_error()
    except MyException as e:
        _, _, tb = sys.exc_info()
        lines = traceback.format_tb(tb)
        print("".join(lines))
        # traceback.print_tb(tb)
        


# test_traceback()
# test_wrapper(n=10, limit=10)
test_sys_exc_info()
