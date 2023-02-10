import logging
import jinja2

from multiprocessing import Pool
from time import sleep

from nepta.core.strategies.generic import Strategy
from nepta.core.distribution.command import Command
from nepta.core.model.schedule import RsyncHost

logger = logging.getLogger(__name__)


class Submit(Strategy):
    # Sticky bit has to be deleted. Otherwise, it cause errors in results manipulation (delete by group user).
    _RSYNC_TEMPLATE = jinja2.Template(
        """rsync -avz --no-owner --no-group --recursive --chmod=a+r,a+w,a+X,o-t {{ path }} \
{{ rsync.server }}::{{ rsync.destination }}"""
    )

    def __init__(self, configuration, package):
        super().__init__()
        self.configuration = configuration
        self.package = package

    @Strategy.schedule
    def submit(self):
        logger.info('Starting rsync results')
        for rsync in self.configuration.get_subset(m_class=RsyncHost):
            logger.info('Rsyncing results to %s', ':'.join([rsync.server, rsync.destination]))
            c = Command(self._RSYNC_TEMPLATE.render(path=self.package.path, rsync=rsync))
            c.run()
            out, ret = c.watch_output()
            if not ret:
                logger.info('Rsync successful')
            else:
                logger.error('Rsync failed')
                logger.error(out)


class ReliableSubmit(Submit):
    @staticmethod
    def _rsync_sender(rsync: RsyncHost, cmd: str):
        for delay in rsync.attempt_delays:
            sleep(delay * 60)
            dest = ':'.join([rsync.server, rsync.destination])
            logger.info(
                f'Rsyncing results to {dest}',
            )

            c = Command(cmd)
            c.run()
            out, ret = c.get_output()
            logger.debug(out)
            if ret == 0:
                logger.info(f'Rsync result to {dest} >> Successful')
                break
            else:
                logger.error(f'Rsync result to {dest} >> Failed')
        else:  # no break
            logger.error(
                f'All rsync attempts to destination {rsync.destination} failed.' f' Result was not sent to data server.'
            )

    @Strategy.schedule
    def submit(self):
        logger.info('Starting reliable rsyncing results to servers')
        rsyncs = list(self.configuration.get_subset(m_class=RsyncHost))

        with Pool(len(rsyncs)) as p:
            p.starmap(
                ReliableSubmit._rsync_sender,
                [(rsync, self._RSYNC_TEMPLATE.render(rsync=rsync, path=self.package.path)) for rsync in rsyncs],
            )

        logging.debug('Quitting reliable rsyncing results to servers')
