from typing import Any


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    def __repr__(self):
        return '<AttrDict ' + dict.__repr__(self) + '>'

    def __getattr__(self, name: str) -> Any:
        if name in self and isinstance(self[name], dict):
            self[name] = AttrDict(self[name])
        return self[name]
