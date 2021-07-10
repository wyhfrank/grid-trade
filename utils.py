import os
import logging
import logging.handlers
from datetime import datetime
import asyncio
import yaml


async def make_async(func, *args):
    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, func, *args)
    return res


def read_config(fn='./configs/config.yml'):
    config = None
    if not os.path.exists(fn):
        raise ValueError(f"Cannot open config file: {fn}")
    
    with open(fn, 'r') as f:
        config = yaml.safe_load(f)
    return config


def create_pine_script(df_history, side_key='side', cost_key='cost', time_key='executed_at', script_title="History", max_lines=200):
    lines = [
        "// @version=4\n\nstudy(\"{}\", overlay=true, max_labels_count=500)\n".format(script_title),
    ]

    count = 0
    for i, row in df_history.iterrows():

        count += 1
        if count > max_lines:
            break

        if row[side_key] == "sell":
            color = "color.red"
            text = "Sell\\n"
            style = 'label.style_labeldown'
            yloc = 'yloc.abovebar'
        elif row[side_key] == "buy":
            color = "color.green"
            text = "Buy\\n"
            style = 'label.style_labelup'
            yloc = 'yloc.belowbar'
        text += "{0:.0f}".format(row[cost_key])

        time = datetime.fromtimestamp(row[time_key]/1000)
        line = 'label.new(timestamp("GMT+9",{time}),close,xloc=xloc.bar_time,' \
               'yloc={yloc},text="{text}",style={style},color={color})' \
            .format(time=",".join(map(str, [time.year, time.month, time.day, time.hour, time.minute])),
                    text=text, color=color, style=style, yloc=yloc)
        lines.append(line)

    return "\n".join(lines)


#############################
# Dynamically add properties
def init_formatted_properties(cls, default_precision=4):
    """ For each of the fields in `fields_to_format` add a new property to the cls
            that formats the float value into proper string
        
        Example:
        Class has fields: f1, f2, f3, and then string property will be generated:
            cls.f1_s ==> 'x.xx'
            cls.f2_s ==> 'x.x'
            cls.f3_s ==> 'x.xx%'

        fields_to_format = {
            'f1': {},
            'f2': {'precision': 1},
            'f3': {'precision': 4, '_type': 'ratio'},
        }
    """
    fields_to_format = 'fields_to_format'
    if not hasattr(cls, fields_to_format):
        raise TypeError(f"Class {cls} need to have a {fields_to_format} field to add `Name_s` properties.")

    def get_formatter(field, precision=2, is_ratio=False):
        # Save the parameters in this closure
        def format_float(obj):
            v = round(getattr(obj, field), precision)
            if is_ratio:
                res = f"{v * 100:.{precision-2}f}%"
            else:
                res = f"{v:.{precision}f}"
            return res
        return property(format_float)

    for field, setting in getattr(cls, fields_to_format).items():
        precision = setting.get('precision', default_precision)
        is_ratio = setting.get('_type', '') == 'ratio'
        setattr(cls, field + '_s', get_formatter(field=field, precision=precision, is_ratio=is_ratio))


#############################
# Logging
def  setup_logging(log_file_path=None, backup_count=30, basic_level=logging.DEBUG, 
                    stream_level=logging.INFO,  file_level=logging.DEBUG):
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(format_str)

    handlers = []
    sh = logging.StreamHandler()
    sh.setLevel(stream_level)
    sh.setFormatter(formatter)
    handlers.append(sh)

    if log_file_path:
        dirname = os.path.dirname(log_file_path)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        fh = logging.handlers.TimedRotatingFileHandler(
            filename=log_file_path, when='midnight', backupCount=backup_count)
        fh.setFormatter(formatter)
        fh.setLevel(file_level)
        handlers.append(fh)

    logging.basicConfig(level=basic_level, handlers=handlers)


def config_logging(logging_config):
    def get_level(name, default):
        return getattr(logging, name) if hasattr(logging, name) else default

    c = logging_config if logging_config else {}
    
    file_config = c.get('file', {})
    file_path = file_config.get('path', None)
    backup_count = file_config.get('backup_count', 10)

    setup_logging(log_file_path=file_path, backup_count=backup_count)



#################
# Tests
def test_logging():
    # setup_logging(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    # logger.setLevel(logging.DEBUG)
    # print(logging.getLevelName(logger.level))
    logger.debug('debug')
    logger.info('info')
    logger.warning('warning')
    logger.error('error')
    logger.critical('critical')


def test_config_logging():
    config = None
    config = {}
    config = {
        'level': 'DEBUG'
    }
    config_logging(config)

    test_logging()


def test_default_counter():
    counter = DefaultCounter()
    # counter['a'] = 1
    # counter['b'] += 2
    print(counter.total)
    print(counter)


if __name__ == '__main__':
    # test_logging()
    # test_config_logging()
    test_default_counter()

