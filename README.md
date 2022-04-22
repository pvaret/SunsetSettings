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
>>> import sunset

>>> # Types can be inferred from the provided default value:
>>> number_of_ponies = sunset.Setting(default=0)

>>> number_of_ponies.set(6)  # Works!
>>> number_of_ponies.set("six")  # Type error!

>>> ponies = number_of_ponies.get()  # 'ponies' correctly typechecks as int
```

### Extensibility

You can store arbitrary types in your SunsetSettings provided they implement a
simple serialization protocol. (See `sunset/protocols.py`.)

```python
>>> import re
>>> from typing import Optional
>>> class Coordinates:
...     def __init__(self, x: int = 0, y: int = 0) -> None:
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

>>> import sunset
>>> coordinates = sunset.Setting(default=Coordinates())
>>> coordinates.get()  # Correctly typechecks to 'Coordinates'.
```

### Inheritance

SunsetSettings lets the user have a general set of settings that can be
partially overriden for specific cases (much like your VSCode settings can be
overriden by workspace, for instance). The hierarchy of inheritance can be
arbitrarily deep.

````python
>>> import sunset
>>> class Animals(sunset.Settings):
...     paws: sunset.Setting[int] = sunset.NewSetting(default=4)
... 
>>> animals = Animals()
>>> octopuses = animals.deriveAs("octopuses")
>>> octopuses.paws.get()
4
>>> octopuses.paws.set(8)
>>> octopuses.paws.get()
8
>>> animals.paws.get()
4
````

### Callbacks

Each setting can be given callbacks to be called when its value changes.

```python
>>> import sunset
>>> number_of_ponies = sunset.Setting(default=0)
>>> def callback(value):
...     print("Pony count updated:", value)
...     
>>> number_of_ponies.onChangeCall(callback)
>>> number_of_ponies.set(6)
Pony count updated: 6
```

## Requirements

- Python 3.9 or later.
- The `typing_extensions` module.
- `flit` for installation from sources.

## Installation

### Installing from PyPI

This is not yet available.

### Installing from sources

1. Download the code:

    `git clone https://github.com/pvaret/SunsetSettings`

2. Install the library:

    `flit install`

That's it.

## API documentation

In progress! Honestly you should not be using SunsetSettings just YET, it's a
work in progress and the API is not stable yet.
