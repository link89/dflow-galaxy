import logging

logging.basicConfig(format='%(asctime)s %(name)s: %(message)s', level=logging.INFO)

def get_logger(name=None):
    return logging.getLogger(name)
