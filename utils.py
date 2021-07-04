import asyncio
import yaml


async def make_async(func, *args):
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, func, *args)
    return res


def read_config(fn='./configs/config.yml'):
    config = None
    with open(fn, 'r') as f:
        config = yaml.safe_load(f)
    return config
