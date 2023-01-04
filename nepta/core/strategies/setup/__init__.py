from nepta.core.model.bundles import HostBundle
from nepta.core.strategies.generic import CompoundStrategy

from nepta.core.strategies.setup.system import SystemSetup
from nepta.core.strategies.setup.packages import Packages
from nepta.core.strategies.setup.network import Network
from nepta.core.strategies.setup.virt import Virtualization


def get_strategy(conf: HostBundle) -> CompoundStrategy:
    strategies = [
        SystemSetup(conf),
        Packages(conf),
        Network(conf),
        Virtualization(conf),
    ]

    return CompoundStrategy.sum(strategies)
