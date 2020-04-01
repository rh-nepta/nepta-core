from . import attachments
from . import meta

from nepta.core.strategies.generic import Strategy


class Save(Strategy):

    def __init__(self, package):
        super().__init__()
        self.package = package

    @Strategy.schedule
    def save(self):
        self.package.close()


def get_strategy(package):
    return Save(package)
