from collections import OrderedDict


class GenericTag(object):

    def __init__(self, name, value=None):
        self.name = name
        self.value = value

    def __repr__(self):
        if self.value:
            return "{}-{}".format(self.name, self.value)
        else:
            return self.name

    def __str__(self):
        return self.__repr__()

    def __add__(self, other):
        return self.__class__('{}-{}'.format(self.__repr__(), other.__repr__()))

    def __lt__(self, other):  # this is needed for sort()
        return self.__repr__() < other.__repr__()


class HardwareInventoryTag(GenericTag):
    pass


class SoftwareInventoryTag(GenericTag):
    pass


