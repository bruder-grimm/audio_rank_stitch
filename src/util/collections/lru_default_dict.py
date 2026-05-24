from collections import OrderedDict

class LRUDefaultDict:
    def __init__(self, default_factory=None, max_size=300):
        self._dict = OrderedDict()
        self.default_factory = default_factory or (lambda: None)
        self.max_size = max_size

    def __getitem__(self, key):
        try:
            value = self._dict[key]
            # Move the accessed item to the end to show that it was recently used
            self._dict.move_to_end(key)
            return value
        except KeyError:
            if len(self._dict) >= self.max_size:
                # Remove the least recently used item
                self._dict.popitem(last=False)
            value = self.default_factory()
            self._dict[key] = value
            return value

    def __setitem__(self, key, value):
        if key in self._dict:
            # Move the existing item to the end and update its value
            self._dict.move_to_end(key)
        elif len(self._dict) >= self.max_size:
            # Remove the least recently used item
            self._dict.popitem(last=False)
        self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]

    def __len__(self):
        return len(self._dict)

    def __contains__(self, key):
        return key in self._dict