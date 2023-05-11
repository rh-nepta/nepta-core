import copy
import logging
import itertools
from collections import OrderedDict, defaultdict
from nepta.core.model.system import Value
from typing import Dict

logger = logging.getLogger(__name__)


class BundleException(Exception):
    pass


class MergeBundleException(BundleException):
    pass


class DupliciteConfException(BundleException):
    pass


class Bundle(object):
    _properties = ['_bundles', '_components', '_parents', '__deepcopy__', '__getstate__']

    def __init__(self, clone=None):
        self._components = []  # configuration objects of this bundle
        self._bundles = OrderedDict()  # tree nodes (children)
        self._parents = []
        if clone is not None:
            self += clone

    def __str__(self):
        return 'Configuration bundle : \n' + '\n'.join([str(x) for x in self.get_all_components()])

    def __iter__(self):
        return self.item_generator()

    def __getitem__(self, item):
        return self.get_all_components()[item]

    def __getattr__(self, key):
        if key in self.__class__._properties:
            return super().__getattribute__(key)
        else:
            if key not in self._bundles:
                setattr(self, key, Bundle())
            return self._bundles[key]

    def __setattr__(self, key, value):
        if key not in self.__class__._properties:
            new_item = not (key in self._bundles and value == self._bundles[key])
            if isinstance(value, list):
                self._bundles[key] = Bundle().add_multiple_components(*value)
            else:
                self._bundles[key] = value
            if isinstance(value, Bundle) and new_item:
                value._parents.append(self)
                if len(value._parents) > 1:
                    logger.warning('You are using cyclic graph structure!!! Be careful!!!')
        else:
            super().__setattr__(key, value)

    def __delattr__(self, item):
        if item not in self.__class__._properties:
            poped = self._bundles.pop(item)
            if isinstance(poped, Bundle):
                poped._parents.remove(self)
        else:
            super().__delattr__(item)

    def __copy__(self):
        local_bundles = self._serialize_by_bfs(bundles_only=True)
        lookup_table = {x: Bundle() for x in local_bundles}

        for local, new in lookup_table.items():
            new._components.extend(local._components)
            for local_child_name, local_child_value in local._bundles.items():
                if isinstance(local_child_value, Bundle):
                    setattr(new, local_child_name, lookup_table[local_child_value])
                else:
                    setattr(new, local_child_name, local_child_value)
        return lookup_table[self]

    def __deepcopy__(self, memodict={}):
        local_bundles = self._serialize_by_bfs(bundles_only=True)
        lookup_table = {x: Bundle() for x in local_bundles}

        for local, new in lookup_table.items():
            new._components.extend(copy.deepcopy(local._components))
            for local_child_name, local_child_value in local._bundles.items():
                if isinstance(local_child_value, Bundle):
                    setattr(new, local_child_name, lookup_table[local_child_value])
                else:
                    setattr(new, local_child_name, copy.deepcopy(local_child_value))
        return lookup_table[self]

    def has_node(self, node_name):
        return node_name in self._bundles

    def item_generator(self):
        for item in self.get_all_components():
            yield item

    def __len__(self):
        return len(self.get_all_components())

    def add_component(self, component):
        self._components.append(component)
        return self

    def add_multiple_components(self, *args):
        self._components.extend(list(args))
        return self

    def get_local_components(self):
        return self._components

    def get_all_components(self):
        """
        Getting all components from tree like structure. We use BFS algorithm  with closed set for tree traversal.
        Configuration objects from each tree node are appended to `component_list`.
        :return: List of all configuration object in tree structure.
        """
        components_list = []

        for node in self._serialize_by_bfs():
            if isinstance(node, Bundle):
                components_list.extend([model for model in node.get_local_components()])
            else:
                components_list.append(node)

        return components_list

    def flush_components(self):
        self._components = []
        self._bundles = {}
        return self

    def clone(self):
        """
        Create a now tree structure and duplicate objects.
        :return:
        """
        return copy.deepcopy(self)

    def copy(self):
        """
        Create a new tree strucutre of Bundles, but objects pointers are the same.
        :return:
        """
        return copy.copy(self)

    def _serialize_by_bfs(self, bundles_only=False):
        open_q = {self}  # set
        closed_q = []
        while len(open_q):
            bundle = open_q.pop()
            closed_q.append(bundle)

            for child in bundle._bundles.values():
                if isinstance(child, Bundle):
                    if child not in closed_q:  # append state into open queue only if it is not already traversed
                        open_q.add(child)
                elif not bundles_only:
                    if type(child) == list:
                        closed_q.extend(child)
                    else:
                        closed_q.append(child)  # leaf model cannot be expanded so they go directly to closed Q
        return closed_q

    def filter_components(self, filter_func):
        for node in self._serialize_by_bfs(bundles_only=True):
            node._components = [cmp for cmp in node._components if filter_func(cmp)]
            for child_name, child_node in list(node._bundles.items()):
                if not isinstance(child_node, Bundle):
                    if not filter_func(child_node):
                        node._bundles.pop(child_name)

        return self

    def get_subset(self, m_class=None, m_type=None, exclude=False):
        def class_and_type_filter(component):
            if m_class and m_type:
                return (isinstance(component, m_class) and type(component) == m_type) ^ exclude
            elif m_class:
                return (isinstance(component, m_class)) ^ exclude
            elif m_type:
                return (type(component) == m_type) ^ exclude
            else:
                return False ^ exclude

        ret_bundle = self.copy()
        ret_bundle.filter_components(class_and_type_filter)
        return ret_bundle

    def merge_bundles(self, other):
        self._components.extend(other._components)
        for attr_name, value in other._bundles.items():
            if isinstance(value, Bundle):
                if attr_name in self._bundles:
                    self._bundles[attr_name].merge_bundles(value)
                else:  # attr is not in local bundle so no merge is necessary
                    setattr(self, attr_name, value.copy())
            else:  # if is not instance of Bundle
                if attr_name in self._bundles:
                    raise MergeBundleException(
                        '%s -> {%s} model is defined in both trees.'
                        ' I do NOT know which should I use.' % (attr_name, value)
                    )
                else:
                    self._bundles[attr_name] = value

    def __iadd__(self, other):
        if isinstance(other, Bundle):
            self.merge_bundles(other)
        elif hasattr(other, '__iter__'):
            self.add_multiple_components(*other)
        else:
            self.add_component(other)
        return self

    def __add__(self, other):
        """
        Create clone of self and add other object to it.
        :param other:
        :return:
        """
        new_bundle = Bundle(self)
        new_bundle += other
        return new_bundle

    def str_tree(self):
        return '\n'.join([str(x) for x in DisplayableNode.from_bundle('RootBundle', self)])


class DisplayableNode(object):
    """
    Inspired by : https://stackoverflow.com/questions/9727673/list-directory-tree-structure-in-python
    """

    child_prefix_middle = '├──'
    child_prefix_last = '└──'
    parent_prefix_middle = '|   '
    parent_prefix_last = '    '

    def __init__(self, name, label, parent, is_last):
        self.name = name
        self.label = label
        self.parent = parent
        self.parent_prefix = self.get_parent_prefix()
        self.is_last = is_last

    @classmethod
    def from_bundle(cls, name, node, parent=None, is_last=False, closed=None):
        if closed is None:
            closed = {}

        if node in closed:
            root = cls(name, closed[node] + ' [cycle]', parent, is_last)
            yield root
            return
        else:
            closed[node] = name
            root = cls(name, None, parent, is_last)
            yield root

        i = 0
        last_id = len(node._bundles.keys()) + len(node.get_local_components()) - 1
        for name, child in node._bundles.items():
            if isinstance(child, Bundle):
                yield from cls.from_bundle(name, child, root, i == last_id, closed)
            elif hasattr(child, '__iter__'):
                yield from cls.from_list(name, child, root, i == last_id)

            else:
                yield cls(name, str(child), root, i == last_id)
            i += 1

        if len(node.get_local_components()):
            yield from cls.from_list('legacy component list', node.get_local_components(), root, True)

    @classmethod
    def from_list(cls, name, container, parent, is_last):
        local_list = cls('{}  #{!s}'.format(name, type(container)), None, parent, is_last)
        last_id = len(container) - 1
        yield local_list
        for index, model in enumerate(container):
            yield cls(index, str(model), local_list, index == last_id)

    def format_label_str(self, kv_separator=' -> ', extra_indent='\t'):
        model_string = str(self.label)
        striped_bundle = [x.strip() for x in model_string.split('\n')]
        parent_continuation = self.parent_prefix_last if self.is_last else self.parent_prefix_middle
        line_delimiter = '\n{}{}{}'.format(self.parent_prefix, parent_continuation, extra_indent)
        return kv_separator + line_delimiter.join(striped_bundle)

    def get_parent_prefix(self):
        parent_prefix_list = []
        parent = self.parent
        while parent and parent.parent is not None:
            parent_prefix_list.append(self.parent_prefix_last if parent.is_last else self.parent_prefix_middle)
            parent = parent.parent
        return ''.join(reversed(parent_prefix_list))

    def __str__(self):
        if self.parent is None:
            return self.name

        bundle_name = '{!s} {!s}'.format(
            self.child_prefix_last if self.is_last else self.child_prefix_middle, self.name
        )
        model_value_str = '' if self.label is None else self.format_label_str()

        return self.parent_prefix + bundle_name + model_value_str


class HostBundle(Bundle):
    _all_confs_register: Dict[str, Dict[str, 'HostBundle']] = defaultdict(dict)
    _properties = Bundle._properties + ['_hostname', '_conf_name']

    @classmethod
    def find(cls, hostname, conf_name):
        if hostname in cls._all_confs_register and conf_name in cls._all_confs_register[hostname]:
            return cls._all_confs_register[hostname][conf_name]

    @classmethod
    def filter_conf(cls, hostname=None, conf_name=None) -> list:
        if hostname is not None:
            if conf_name is None:
                return list(cls._all_confs_register[hostname].values())
            else:
                conf = cls.find(hostname, conf_name)
                return [conf] if conf is not None else []
        else:
            # get lists of conf list
            # and convert it into single list
            all_confs = itertools.chain.from_iterable(
                [list(host_conf.values()) for host_conf in cls._all_confs_register.values()]
            )
            if conf_name is None:
                return list(all_confs)
            else:
                return [conf for conf in all_confs if conf.conf_name == conf_name]

    @classmethod
    def _add_configuration(cls, conf):
        if cls.find(conf.hostname, conf.conf_name) is None:
            cls._all_confs_register[conf.hostname][conf.conf_name] = conf
        else:
            raise DupliciteConfException(f'Configuration {conf.hostname} {conf.conf_name} already exists')

    def __init__(self, hostname, conf_name, clone=None):
        self._hostname = hostname
        self._conf_name = conf_name
        super(HostBundle, self).__init__(clone)

        self._add_configuration(self)

    def __str__(self):
        return 'Host configuration bundle : \n' + '\n'.join([str(x) for x in self.get_all_components()])

    @property
    def hostname(self):
        return self._hostname

    @property
    def conf_name(self):
        return self._conf_name

    def get_hostname(self):
        return self._hostname

    def get_conf_name(self):
        return self._conf_name


class SyncHost:
    def __init__(self, hostname):
        self._hostname = hostname

    def __str__(self):
        return 'Sync host: %s' % self._hostname

    @property
    def hostname(self):
        return self._hostname

    def get_hostname(self):
        return self._hostname

    @classmethod
    def sync_all(cls, *args: HostBundle, subtree='sync'):
        for a, b in itertools.permutations(args, 2):
            getattr(a, subtree).add_component(cls(b.hostname))


class SyncServer(Value):
    pass
