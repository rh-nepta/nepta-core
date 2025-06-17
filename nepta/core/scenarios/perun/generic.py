import logging
import os
import pathlib

from nepta.core.scenarios.generic.scenario import StreamGeneric
from nepta.core.distribution.utils.perf import Perf

logger = logging.getLogger(__name__)


class PerunMixin(StreamGeneric):
    def __init__(self, *args, **kwargs):
        self.perun_directory = os.path.join(
            kwargs.pop('perun_directory', '/tmp/perun'),
            self.__class__.__name__,
        )
        super().__init__(*args, **kwargs)

    def run_scenario(self):
        pathlib.Path(self.perun_directory).mkdir(parents=True, exist_ok=True)
        return super().run_scenario()


class PerunBpfMixin(PerunMixin):
    def run_scenario(self):
        results = super().run_scenario()
        # rename perf data files for compatibility with perf fold
        logger.info('Renaming perf data')
        for perf_file in pathlib.Path(self.perun_directory).rglob('*.perf.data'):
            logger.debug(f'Renaming {perf_file}!')
            os.rename(perf_file, f"{perf_file}.folded")
        return results


class PerunPerfMixin(PerunMixin):

    def run_scenario(self):
        results = super().run_scenario()

        # fold perf data
        logger.info('Folding perf data')
        for perf_file in pathlib.Path(self.perun_directory).rglob('*.perf.data'):
            logger.debug(f'Folding {perf_file}')
            Perf.fold_output(perf_file, f"{perf_file}.folded")
            logger.debug(f'Deleting {perf_file}!')
            os.remove(perf_file)
        return results
