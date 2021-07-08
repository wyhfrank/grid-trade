import logging
import logging.handlers


def spit(logger):
    for i in range(10):
        logger.debug('debug')
        logger.info('info')
        logger.warning('warning')
        logger.error('error')
        # logger.exception('exception')
        logger.critical('critical')


def setup_logging(level=logging.INFO):
    logging.basicConfig(level=level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                        datefmt='%Y-%m-%d %H:%M:%S')

def setup_file_handler(basic_level=logging.INFO, stream_level=logging.INFO,  file_level=logging.INFO, log_file_path='./logs/app.log', backup_count=30):
    format_f='INFILE: %(asctime)s - %(name)s - %(levelname)s - %(message)s'
    format_s='STREAM: %(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter_f = logging.Formatter(format_f)
    formatter_s = logging.Formatter(format_s)

    sh = logging.StreamHandler()
    sh.setLevel(stream_level)
    sh.setFormatter(formatter_s)

    fh = logging.handlers.TimedRotatingFileHandler(
        filename=log_file_path, when='midnight', backupCount=backup_count)
    fh.setFormatter(formatter_f)
    fh.setLevel(file_level)

    logging.basicConfig(level=basic_level, handlers=[
        sh, 
        fh
        ])
    # This is equivalent to the following 3 lines

    # logging.root.setLevel(basic_level)
    # logging.root.addHandler(sh)
    # logging.root.addHandler(fh)


def my_solution():
    module_logger = logging.getLogger('a module')

    assert logging.root.level == logging.WARN
    assert module_logger.level == logging.NOTSET

    # spit(module_logger)

    basic_level=logging.DEBUG
    stream_level=logging.INFO
    file_level=logging.DEBUG
    max_size = 1
    setup_file_handler(basic_level=basic_level, stream_level=stream_level,  file_level=file_level, max_size=max_size)

    assert logging.root.level == basic_level
    assert module_logger.level == logging.NOTSET
    assert module_logger.getEffectiveLevel() == basic_level
    spit(module_logger)
    

my_solution()
exit()

def test_parent():
    lab = logging.getLogger('a.b')
    assert lab.parent == logging.root
    
    la = logging.getLogger('a')
    assert lab.parent == la

# test_parent()

def test_notset_level():
    toto_logger = logging.getLogger("toto")
    assert toto_logger.level == logging.NOTSET # new logger has NOTSET level
    assert toto_logger.getEffectiveLevel() == logging.WARN # and its effective level is the root logger level, i.e. WARN

    # attach a console handler to toto_logger
    console_handler = logging.StreamHandler()
    toto_logger.addHandler(console_handler)
    toto_logger.debug("debug") # nothing is displayed as the log level DEBUG is smaller than toto effective level
    toto_logger.setLevel(logging.DEBUG)
    toto_logger.debug("debug message") # now you should see "debug message" on screen

# test_notset_level()


# Best practices from: https://www.toptal.com/python/in-depth-python-logging
# Probably not suitable for my requirements, since the logging level is read from a config file dynamically
def test_best_practice():
    import logging
    import sys
    from logging.handlers import TimedRotatingFileHandler

    FORMATTER = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    LOG_FILE = "my_app.log"

    def get_console_handler():
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(FORMATTER)
        return console_handler

    def get_file_handler():
        file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
        file_handler.setFormatter(FORMATTER)
        return file_handler

    def get_logger(logger_name):
        logger = logging.getLogger(logger_name)

        logger.setLevel(logging.DEBUG) # better to have too much log than not enough

        logger.addHandler(get_console_handler())
        logger.addHandler(get_file_handler())

        # with this pattern, it's rarely necessary to propagate the error up to parent
        logger.propagate = False

        return logger

