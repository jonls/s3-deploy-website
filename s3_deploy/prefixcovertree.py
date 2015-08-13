
"""Data structure for identifying the smallest set of covering prefixes."""

import logging

from six.moves import zip


logger = logging.getLogger(__name__)


def common_prefix(s1, s2):
    """Return the common prefix of strings s1 and s2."""
    prefix = []
    for c1, c2 in zip(s1, s2):
        if c1 != c2:
            break
        prefix.append(c1)
    return ''.join(prefix)


class _Node(object):
    """Node in the prefix trie.

    When the node value is set to False the value propagates up the chain
    of ancestors.
    """
    def __init__(self, key, parent=None, leaf=True, value=True):
        self.key = key
        self._value = value
        self.leaf = leaf
        self.parent = parent
        self.children = set()

        # Propagate value
        self._propagate_value()

    def _propagate_value(self):
        """Propagate the value of the node to ancestor nodes."""
        node = self.parent
        while node is not None:
            if self._value >= node._value:
                break
            node._value = self._value
            node = node.parent

    @property
    def value(self):
        """Node value."""
        return self._value

    @value.setter
    def value(self, v):
        if not isinstance(v, bool):
            raise ValueError('Value must be True or False')
        if self._value < v:
            raise ValueError('Cannot replace node value {}'.format(
                self._value))

        self._value = v
        self._propagate_value()

    def __str__(self):
        key = []
        node = self
        while node is not None:
            key.append(node.key)
            node = node.parent
        return ''.join(reversed(key))

    def __repr__(self):
        return '<{} {}, value={}, leaf={}>'.format(
            self.__class__.__name__, repr(self._key), repr(self._value),
            repr(self.leaf))


class PrefixCoverTree(object):
    """Prefix tree that identifies smallest set of covering prefixes."""
    def __init__(self):
        self._root = _Node('', leaf=False)

    def _iter_nodes(self):
        stack = [self._root]
        while len(stack) > 0:
            node = stack.pop()
            yield node
            stack.extend(sorted(
                node.children, key=lambda n: n.key, reverse=True))

    def include(self, key):
        """Mark a key for inclusion in the covering set."""
        self._set_value(key, True)

    def exclude(self, key):
        """Mark a key for exclusion from the covering set."""
        self._set_value(key, False)

    def matches(self):
        """Iterate over the covering prefix matches.

        Yields tuples of a prefix and an ``exact`` flag. The exact flag
        indicates whether the prefix matches one exact key (True) or a
        subtree of keys (False).
        """
        if len(self._root.children) == 0 and not self._root.leaf:
            return

        for node in self._iter_nodes():
            if node.value and (node.parent is None or not node.parent.value):
                if len(node.children) > 0:
                    yield str(node), False
                else:
                    yield str(node), True

    def _set_value(self, key, value):
        if key == '':
            self._root.value = value
            self._root.leaf = True
            return

        parent = self._root
        while True:
            for node in parent.children:
                prefix = common_prefix(key, node.key)
                if len(prefix) > 0:
                    key_tail = key[len(prefix):]
                    node_tail = node.key[len(prefix):]
                    if len(key_tail) == 0 and len(node_tail) == 0:
                        node.value = value
                        return
                    elif len(node_tail) == 0:
                        key = key_tail
                        parent = node
                        break
                    else:
                        node_1 = _Node(node_tail, parent=node,
                                       value=node.value, leaf=node.leaf)
                        for child in node.children:
                            child.parent = node_1
                        node_1.children = node.children
                        node.key = prefix
                        node.children = {node_1}
                        node.leaf = False
                        node.children.add(
                            _Node(key_tail, parent=node, value=value))
                        return
            else:
                parent.children.add(_Node(key, parent=parent, value=value))
                break

    def __iter__(self):
        for node in self._iter_nodes():
            if node.leaf:
                yield str(node)
