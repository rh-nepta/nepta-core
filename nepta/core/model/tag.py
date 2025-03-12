from dataclasses import dataclass
from typing import Optional
from functools import total_ordering


@total_ordering
@dataclass(repr=False, unsafe_hash=True)
class GenericTag:
    name: str
    value: Optional[str] = None

    def __repr__(self):
        if self.value:
            return "{}-{}".format(self.name, self.value)
        else:
            return self.name

    def __eq__(self, other):
        if not isinstance(other, GenericTag):
            raise NotImplementedError
        return self.name == other.name and self.value == other.value

    def __lt__(self, other: "GenericTag"):
        return self.__repr__() < other.__repr__()

    def __str__(self):
        return self.__repr__()

    def __add__(self, other):
        return self.__class__("{}-{}".format(self.__repr__(), other.__repr__()))


class HardwareInventoryTag(GenericTag):
    pass


class SoftwareInventoryTag(GenericTag):
    pass
