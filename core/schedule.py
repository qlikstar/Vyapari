import datetime
import logging
from enum import Enum
from traceback import format_exc

from kink import inject
from schedule import Scheduler

logger = logging.getLogger('schedule')
logger.setLevel(level=logging.INFO)


class JobRunType(Enum):
    STANDARD = "STANDARD"
    HEARTBEAT = "HEARTBEAT"
    RUN_NOW = "RUN_NOW"


@inject
class SafeScheduler(Scheduler):
    """
    An implementation of Scheduler that catches jobs that fail, logs their
    exception tracebacks as errors, optionally reschedules the jobs for their
    next run time, and keeps going.
    Use this to run jobs that may or may not crash without worrying about
    whether other jobs will run or if they'll crash the entire script.
    """

    def __init__(self, reschedule_on_failure=True):
        """
        If reschedule_on_failure is True, jobs will be rescheduled for their
        next run as if they had completed successfully. If False, they'll run
        on the next run_pending() tick.
        """
        self.reschedule_on_failure = reschedule_on_failure
        super().__init__()

    def _run_job(self, job):
        try:
            super()._run_job(job)
        except Exception:
            logger.error(format_exc())
            job.last_run = datetime.datetime.now()
            job._schedule_next_run()

    def run_adhoc(self, job, run_every_x_secs: int, run_until: str, frequency_tag: JobRunType):
        self.every(run_every_x_secs) \
            .seconds.until(run_until) \
            .do(job) \
            .tag(frequency_tag.value)
