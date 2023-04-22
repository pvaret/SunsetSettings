# SunsetSettings

[![Build Status](https://github.com/pvaret/SunsetSettings/actions/workflows/python-build.yml/badge.svg)](https://github.com/pvaret/SunsetSettings/actions/workflows/python-build.yml)
[![Documentation Status](https://readthedocs.org/projects/sunsetsettings/badge/?version=latest)](https://sunsetsettings.readthedocs.io/en/latest/?badge=latest)

SunsetSettings is a library that provides facilities to declare and use settings
for an interactive application in a *type-safe* manner, and load and save them
in a simple INI-like format.

The settings can safely store arbitrary types, and can be structured in an
arbitrarily deep hierarchy of subsections, which allows you to implement
overrides per project, per folder, per user, etc.

It is mainly intended for software where the user can change settings on the
fly, for instance with a settings dialog, and those settings need to be
preserved between sessions.


## Examples

Creating settings:

```python
>>> from sunset import Bunch, Key, List, Settings

>>> class BackupToolSettings(Settings):
...
...     class UI(Bunch):
...
...         class Font(Bunch):
...             name = Key(default="Arial")
...             size = Key(default=12)
...
...         font  = Font()
...         theme = Key(default="") 
...
...     class Backup(Bunch):
...         folder      = Key(default="~")
...         destination = Key(default="/mnt/backups")
...         compress    = Key(default=True)
...
...     ui = UI()
...     backups = List(Backup())

```

Loading and saving settings:

```python
>>> from sunset import AutoSaver

>>> def main_program_loop(settings: BackupToolSettings):
...     ...

>>> settings = BackupToolSettings()
>>> with AutoSaver(settings, "~/.config/backup.conf"):  # doctest: +SKIP
...    main_program_loop(settings)

```

Using settings values:

```python
>>> def do_backup(source: str, destination: str, use_compression: bool):
...     ...

>>> def do_all_backups(settings: BackupToolSettings):
...     for backup in settings.backups:
...         do_backup(
...             source=backup.folder.get(),
...             destination=backup.destination.get(),
...             use_compression=backup.compress.get(),
...         )

>>> do_all_backups(settings)

```

Changing settings values:

```python
>>> def update_font_settings(
...     font_name: str,
...     font_size: int,
...     font_settings: BackupToolSettings.UI.Font,
... ):
...     font_settings.name.set(font_name)
...     font_settings.size.set(font_size)

>>> update_font_settings("Verdana", 11, settings.ui.font)

```

Reacting to setting value changes:

```python
>>> def apply_theme(new_theme_name: str):
...     ...

>>> def setup_theme_change_logic(ui_settings: BackupToolSettings.UI):
...     ui_settings.theme.onValueChangeCall(apply_theme)

>>> setup_theme_change_logic(settings.ui)

```


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
True
>>> number_of_ponies.set("six")  # Type error!
False
>>> number_of_ponies.get()  # Value is unchanged.
6
>>> from typing import TYPE_CHECKING
>>> if TYPE_CHECKING:
...     reveal_type(number_of_ponies.get())
>>> # Revealed type is "builtins.int"

```


### Extensibility

You can store arbitrary types in your SunsetSettings provided that you also
provide a serializer for that type. (See [the API
reference](https://sunsetsettings.rtfd.io/en/stable/api.html#sunset.Serializer).)

```python
>>> import re
>>> from typing import Optional, TYPE_CHECKING

>>> class Coordinates:
...     def __init__(self, x: int, y: int) -> None:
...         self.x = x
...         self.y = y

>>> class CoordinatesSerializer:
...     def toStr(self, coord: Coordinates) -> str:
...         return f"{coord.x},{coord.y}"
...
...     def fromStr(self, string: str) -> Optional[Coordinates]:
...         x, y = string.split(",", 1)
...         if not x.isdigit() or not y.isdigit():
...             return None
...         return Coordinates(int(x), int(y))

>>> from sunset import Key
>>> coordinates = Key(
...     default=Coordinates(0, 0), serializer=CoordinatesSerializer()
... )
>>> if TYPE_CHECKING:
...     reveal_type(coordinates.get())
>>> # Revealed type is "Coordinates"
>>> print(repr(coordinates))
<Key[Coordinates]:(0,0)>

```


### Inheritance

SunsetSettings lets the user have a general set of settings that can be
partially overriden in subsections used in specific cases (much like your VSCode
settings can be overriden by workspace, for instance). The hierarchy of
subsections can be arbitrarily deep.

```python
>>> from sunset import Key, Settings

>>> class Animals(Settings):
...     limbs: Key[int] = Key(default=4)
... 
>>> animals = Animals()
>>> octopuses = animals.newSection(name="octopuses")
>>> octopuses.limbs.get()
4
>>> octopuses.limbs.set(8)
True
>>> octopuses.limbs.get()
8
>>> animals.limbs.get()
4
>>> octopuses.limbs.clear()
>>> octopuses.limbs.get()
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
True

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

The API documentation is available at https://sunsetsettings.readthedocs.io/.
