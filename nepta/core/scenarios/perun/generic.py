from typing import Tuple, List, Union
import logging
import uuid

from nepta.core.model.schedule import PathList, Path
from nepta.core.scenarios.generic.scenario import StreamGeneric
from nepta.dataformat import Section

logger = logging.getLogger(__name__)


class GenericPerun(StreamGeneric):

    def __init__(
            self,
            paths: Union[List[Path], PathList],
            test_length: int,
            msg_sizes: List[int],
            reversed: bool = False,
            cpu_pinning: Tuple[int] = (1, 1),
            base_port: int = 5201,
    ):
        self.reverse = reversed
        super().__init__(paths, test_length, 1, msg_sizes, cpu_pinning, base_port, 1, 0)

    def run_instance(self, path: Path, size: int) -> Section:

    def store_instance(self, section, test):
        pass

    def get_test_command(self, path: Path, size: int) -> str:
        return f"iperf3 -c {path.dst_ip} -p {self.base_port} -t {self.test_length} -n {size} -P 1"


class GenericMultiStreamPerun(GenericPerun): ...
