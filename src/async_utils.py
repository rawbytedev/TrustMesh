import asyncio
import logging

log = logging.getLogger(__name__)

def _task_done_cb(task: asyncio.Task):
    try:
        exc = task.exception()
        if exc:
            log.exception("Task failed", exc_info=exc)
    except asyncio.CancelledError:
        pass

def create_monitored_task(coro, *, name=None):
    task = asyncio.create_task(coro, name=name)
    task.add_done_callback(_task_done_cb)
    return task

def set_loop_exception_handler(loop=None):
    loop = loop or asyncio.get_event_loop()
    def _handler(loop, context):
        logging.getLogger("asyncio").error("Unhandled exception in loop: %s", context)
    loop.set_exception_handler(_handler)