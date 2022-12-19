# SunsetSettings

[![SunsetSettings](https://circleci.com/gh/pvaret/SunsetSettings.svg?style=shield)](https://circleci.com/gh/pvaret/SunsetSettings)

SunsetSettings is a Python library that lets you define, load and save settings
in a *type-safe* manner.

It is mainly intended for software where the user can change settings on the
fly, for instance with a settings dialog, and those settings need to be
preserved between sessions.

## Features

### Type safety

SunsetSettings is type-safe; that is to say, if you are holding it wrong, type
checkers will tell you.

```python
>>> from sunset import Key

>>> # Types can be inferred from the provided default value:
>>> number_of_ponies = Key(default=0)
>>> number_of_ponies
<Key[int]:(0)>
>>> number_of_ponies.set(6)  # Works!
>>> number_of_ponies.set("six")  # Type error!
>>> number_of_ponies.get()  # Value is unchanged.
6
>>> from typing import TYPE_CHECKING
>>> if TYPE_CHECKING:
...     reveal_type(number_of_ponies.get())
>>> # Revealed type is "builtins.int"

```


### Extensibility

You can store arbitrary types in your SunsetSettings provided they implement a
simple serialization protocol. (See `sunset/protocols.py`.)

```python
>>> import re
>>> from typing import Optional, TYPE_CHECKING
>>> class Coordinates:
...     def __init__(self, x: int, y: int) -> None:
...         self._x = x
...         self._y = y
...
...     def toStr(self) -> str:
...         return f"{self._x},{self._y}"
...
...     @classmethod
...     def fromStr(cls, value: str) -> Optional["Coordinates"]:
...         m = re.match(r"(\d+),(\d+)", value)
...         if m is None:
...             return None
...         x = int(m.group(1))
...         y = int(m.group(2))
...         return cls(x, y)

>>> from sunset import Key
>>> coordinates = Key(default=Coordinates(0, 0))
>>> if TYPE_CHECKING:
...     reveal_type(coordinates.get())
>>> # Revealed type is "Coordinates"

```


### Inheritance

SunsetSettings lets the user have a general set of settings that can be
partially overriden for specific cases (much like your VSCode settings can be
overriden by workspace, for instance). The hierarchy of inheritance can be
arbitrarily deep.

```python
>>> from sunset import Key, Settings
>>> class Animals(Settings):
...     paws: Key[int] = Key(default=4)
... 
>>> animals = Animals()
>>> octopuses = animals.newSection(name="octopuses")
>>> octopuses.paws.get()
4
>>> octopuses.paws.set(8)
>>> octopuses.paws.get()
8
>>> animals.paws.get()
4

```


### Callbacks

Each setting key can be given callbacks to be called when its value changes.

```python
>>> from sunset import Key
>>> number_of_ponies = Key(default=0)
>>> def callback(value):
...     print("Pony count updated:", value)
>>> number_of_ponies.onValueChangeCall(callback)
>>> number_of_ponies.set(6)
Pony count updated: 6

```


## Requirements

- Python 3.9 or later.
- If installing from sources:
    - The `flit` build tool.


## Installation

### Installing from PyPI (recommended)

Run:

```
pip install SunsetSettings
```

This will install the latest version of SunsetSettings, with its required
dependencies.


### Installing from sources

1. Download the code:

    ```
    git clone https://github.com/pvaret/SunsetSettings
    ```

2. Install the library:

    ```
    cd SunsetSettings ; flit install
    ```

That's it.


## API documentation

The API documentation is available at https://sunsetsettings.readthedocs.io/en/latest/.
