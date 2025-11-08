import logging
from logging.handlers import RotatingFileHandler

def setup_logging(level=logging.INFO, logfile="trutmesh.log"):
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    
    fmt = "%(asctime)s %(levelname)s %(name)s %(message)s"
    formatter = logging.Formatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    fh = RotatingFileHandler(logfile, maxBytes=10_000_000, backupCount=3)
    fh.setFormatter(formatter)
    root.setLevel(level)
    root.addHandler(sh)
    root.addHandler(fh)

    logging.captureWarnings(True)

def shutdown_logging():
    root = logging.getLogger()
    for h in list(root.handlers):
        try:
            h.flush()
            h.close()
        except Exception:
            pass
        root.removeHandler(h)