import itertools
from logging import getLogger
from typing import Dict, List, Sequence

logger = getLogger(__name__)


class Strategy:
    """
    This is generic object for strategies used by network performance testing. It defines interface of strategies
    and generic math operations (sum +), which is used to created single huge CompoundStrategy.

    It also encapsulates several auxiliary class/methods, which serve as decorators. These decorators should be applied
    on child classes of Strategy class.
    """

    SCHEDULE_ATTR = '_scheduled'
    METHOD_COUNTER = itertools.count()
    METHOD_INDEX: Dict[str, int] = {}

    def __init__(self):
        super().__init__()
        self.func_list = self.find_scheduled()

    def __call__(self):
        for func in self.func_list:
            logger.info(f'Executing {self.__class__.__name__}.{func}')
            getattr(self, func)()

    def __add__(self, other):
        """
        Strategy + Strategy = CompoundStrategy
        :param other: other strategy
        :return: Compound strategy of self and other
        """
        compound_strategy = CompoundStrategy(self)
        compound_strategy += other
        return compound_strategy

    def find_scheduled(self):
        """
        This methods search scheduled methods in list of local methods. Names of methods marked by Strategy.schedule
        decorator are returned in list.
        :return: list of names of scheduled methods
        """
        # return [func for func in dir(self) if hasattr(getattr(self, func), self.__class__.SCHEDULE_ATTR)]
        ret_list = []
        for func in dir(self):
            if hasattr(getattr(self, func), Strategy.SCHEDULE_ATTR):
                ret_list.append(func)
        ret_list.sort(key=lambda x: getattr(getattr(self, x), Strategy.SCHEDULE_ATTR))
        return ret_list

    @staticmethod
    def schedule(func):
        """
        This is a decorator used for scheduling methods into strategy list of called methods. It set special
        attribute of decorated function, which is used for recognition of scheduled methods.
        :param func: Original function
        :return: Decorated function
        """
        if func.__name__ in Strategy.METHOD_INDEX.keys():
            func_order = Strategy.METHOD_INDEX[func.__name__]
        else:
            func_order = next(Strategy.METHOD_COUNTER)
            Strategy.METHOD_INDEX[func.__name__] = func_order
        setattr(func, Strategy.SCHEDULE_ATTR, func_order)
        return func


class CompoundStrategy:
    """
    This class store reference on several Strategy objects. Objects of this class are callable. When this object
    is called, it cycles through scheduled strategies and __call__ it with provided arguments.
    """

    def __init__(self, strategy=None):
        self.strategies = []
        if strategy:
            self.strategies.append(strategy)

    def __add__(self, other):
        new_com_strat = CompoundStrategy()
        new_com_strat += self
        new_com_strat += other
        return new_com_strat

    def __iadd__(self, other):
        if other.__class__ == CompoundStrategy:
            self.strategies += other.strategies
        else:
            self.strategies.append(other)
        return self

    def __call__(self):
        for strategy in self.strategies:
            logger.info(f'Running strategy {strategy.__class__.__name__}')
            strategy()

    @classmethod
    def sum(cls, strategies: Sequence[Strategy]) -> 'CompoundStrategy':
        compound = cls()
        for s in strategies:
            compound += s
        return compound
