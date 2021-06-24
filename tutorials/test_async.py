# https://stackoverflow.com/a/43263397/1938012
# https://stackoverflow.com/a/38563919/1938012

import asyncio
import time


def something_heavy(count=3):
    print(f"Start with {count}")
    time.sleep(count)
    print(f"End with {count}")
    return count


async def async_heavy1(count):
    # https://stackoverflow.com/a/38563919/1938012
    return asyncio.coroutine(something_heavy)(count=count)

async def async_heavy2(func, *args):
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, func, *args)
    return res


async def runner():
    tasks = []
    # loop = asyncio.get_event_loop()
    for i in range(1, 4):
        # tasks.append(asyncio.ensure_future(async_heavy1(i)))
        tasks.append(asyncio.ensure_future(async_heavy2(something_heavy, i)))
    
    results = await asyncio.gather(*tasks)
    print(results)
    


def main():
    asyncio.run(runner())


main()

