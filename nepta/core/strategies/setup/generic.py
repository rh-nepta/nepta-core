from nepta.core.strategies.generic import Strategy
from nepta.core.model.bundles import HostBundle


class _GenericSetup(Strategy):
    def __init__(self, conf: HostBundle):
        super().__init__()
        self.conf = conf
