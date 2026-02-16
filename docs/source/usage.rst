Usage
=====

Overview
--------

SunsetSettings provides facilities to:

* Describe your app's settings with a type-safe API;
* Load and save settings from and to text files;
* Specialize your app's settings hierarchically per user, per site, per folder,
  etc;
* Call functions when a setting's value changes.


Creating settings
-----------------

Basics
~~~~~~

Settings are created by subclassing the :class:`~sunset.Settings` class and adding
:class:`~sunset.Key` fields to it, in the same way you would with a `standard Python
dataclass <https://docs.python.org/3/library/dataclasses.html>`_.

.. note::
    Under the hood, `Settings` is, in fact, a dataclass, and is used in much the same
    way. Unlike normal dataclasses, adding type annotations is not mandatory:
    SunsetSettings infers the type of your settings automatically. Also unlike a
    dataclass, manually adding `field()` attributes will not work as intended.

.. code-block:: python

    >>> from sunset import Key, Settings

    >>> class MySettings(Settings):
    ...    server = Key(default="127.0.0.1")
    ...    port   = Key(default=80)
    ...    ssl    = Key(default=False)

Note that you add Key instances as class attributes. Note also that Keys need to be
instantiated with a default value. SunsetSettings infers the type of a Key from its
default value.

Type annotations are not mandatory, but can be used, and are generally a good idea:

.. code-block:: python

    >>> from sunset import Key, Settings

    >>> class MySettings(Settings):
    ...     server: Key[str] = Key(default="127.0.0.1")
    ...     port: Key[int]   = Key(default=80)
    ...     ssl: Key[bool]   = Key(default=False)

The benefit of using explicit type annotations is that they serve as a declaration of
intention for what the Keys will hold, and will cause a type error if a given default
does not match the intended type of its Key.

By default, a Key can contain a `str`, an `int`, a `float`, a `bool`, or an `enum.Enum`
subclass. But Keys can also contain any arbitrary type, so long as they are instantiated
with a :class:`~sunset.Serializer` argument for that type. See
:ref:`storing-custom-types`.

Related keys can be grouped together with the :class:`~sunset.Bunch` class.


Bunches
~~~~~~~

A :class:`~sunset.Bunch` provides a way to group together related Keys. This allows you
to pass only that group of Keys to the relevant parts of your application, so that those
parts can remain decoupled. For instance, you could have one Bunch for UI-related Keys,
one for network-related Keys, etc.

For example:

.. code-block:: python

    >>> from sunset import Bunch, Key, Settings

    >>> class Font(Bunch):
    ...     font_name: Key[str] = Key(default="Arial")
    ...     font_size: Key[int] = Key(default=14)

    >>> class Network(Bunch):
    ...     server: Key[str] = Key(default="127.0.0.1")
    ...     port: Key[int]   = Key(default=80)
    ...     ssl: Key[bool]   = Key(default=False)

    >>> class MySettings(Settings):
    ...     font    = Font()
    ...     network = Network()

Here too, type annotations are optional, but can be used, and are a good idea:

.. code-block:: python

    >>> class MySettings(Settings):
    ...     font: Font       = Font()
    ...     network: Network = Network()

.. warning::

    Note that the Bunch fields *have* to be instantiated in the Settings class
    definition, else you will encounter strange bugs that will confuse you. If you
    encounter problems where modifying the value of a Key in a Bunch also changes the
    value of the corresponding Key in another Bunch, make sure that your Bunch fields
    are properly instantiated.

    Using type annotations for Bunch fields ensures that the type checker will catch
    un-instantiated Bunches.

Bunches can be nested within other Bunches:

.. code-block:: python

    >>> class Colors(Bunch):
    ...     bg_color: Key[str] = Key(default="#ffffff")
    ...     fg_color: Key[str] = Key(default="#000000")

    >>> class Font(Bunch):
    ...     font_name: Key[str] = Key(default="Arial")
    ...     font_size: Key[int] = Key(default=14)

    >>> class UI(Bunch):
    ...     colors: Colors = Colors()
    ...     font: Font     = Font()

It is possible and safe to have multiple Bunch fields instantiated from the same Bunch
class:

.. code-block:: python

    >>> class MySettings(Settings):
    ...     input_ui: UI  = UI()
    ...     output_ui: UI = UI()

These Bunch instances are independent from one another, that is to say, their Keys will
not be sharing values.

Variable numbers of Keys or Bunches of the same type can be stored using the
:class:`~sunset.List` class.


Lists
~~~~~

:class:`~sunset.List` provides a container that is type-compatible with Python lists,
and can store Keys or Bunches.

A List is created by passing it an *instantiated* Key or Bunch as its argument. This Key
or Bunch instance will serve as a template for new items in the List, but the template
itself does not get added to the List. Lists are created empty.

The type of the template Key or Bunch determines the type of the List. A List can only
hold items of the same type as its template item.

For example:

.. code-block:: python

    >>> from sunset import Bunch, Key, List, Settings

    >>> class Color(Bunch):
    ...     name: Key[str]    = Key(default="black")
    ...     hexcode: Key[str] = Key(default="#000000")

    >>> class MySettings(Settings):
    ...     colors = List(Color())
    ...     shapes = List(Key(default="square"))


Here too, type annotations are not mandatory but can be used, and provide extra safety
by making your intent explicit:

.. code-block:: python

    >>> class MySettings(Settings):
    ...     colors: List[Color]    = List(Color())
    ...     shapes: List[Key[str]] = List(Key(default="square"))

.. note::

    Why use a SunsetSettings List in your Settings instead of a regular Python list?
    There are a few reasons.

    * SunsetSettings Lists are type-safe even without an explicit type
      annotation.
    * SunsetSettings Lists offer :meth:`~sunset.List.appendOne()` and
      :meth:`~sunset.List.insertOne()` convenience methods to create and add to
      the List an instance of the type held in the List.
    * SunsetSettings Lists support :ref:`layering`.
    * Perhaps most importantly, SunsetSettings knows how to load and save Lists.


.. _storing-custom-types:

Storing custom types in Keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can store any arbitrary type in a Key. There are two ways to do so.

The first way is to provide a serializer when instantiating the Key. A serializer is an
object that implements the :class:`~sunset.Serializer` protocol for the type you want to
store in a Key.

For example:

.. code-block:: python

    >>> from typing import Optional
    >>> from sunset import Key, Settings

    >>> class Coordinates:
    ...     def __init__(self, x: int, y: int) -> None:
    ...         self.x = x
    ...         self.y = y

    >>> class CoordinatesSerializer:
    ...     def toStr(self, coord: Coordinates) -> str:
    ...         return f"{coord.x},{coord.x}"
    ...
    ...     def fromStr(self, string: str) -> Optional[Coordinates]:
    ...         x, y = string.split(",", 1)
    ...         if not x.isdigit() or not y.isdigit():
    ...             return None
    ...         return Coordinates(int(x), int(y))

    >>> class MySettings(Settings):
    ...     origin: Key[Coordinates] = Key(
    ...         Coordinates(0, 0), serializer=CoordinatesSerializer()
    ...     )

    >>> settings = MySettings()
    >>> print(repr(settings.origin))
    <Key[Coordinates]:(0,0)>


The second way is to have the type you want to store in a Key implement the
:class:`~sunset.Serializable` protocol. Note that the methods of this protocol are
pretty similar to that of :class:`~sunset.Serializer`. The difference is that in the
case of :class:`~sunset.Serializable`, the methods are implemented directly on the type
that will be stored in the Key.

For example:

.. code-block:: python

    >>> import re
    >>> from typing import Optional

    >>> from sunset import Key, Settings

    >>> class Coordinates:
    ...     def __init__(self, x: int, y: int) -> None:
    ...         self.x = x
    ...         self.y = y
    ...
    ...     def toStr(self) -> str:
    ...         return f"{self.x},{self.y}"
    ...
    ...     @classmethod
    ...     def fromStr(cls, string: str) -> Optional["Coordinates"]:
    ...         x, y = string.split(",", 1)
    ...         if not x.isdigit() or not y.isdigit():
    ...             return None
    ...         return cls(int(x), int(y))

    >>> class MySettings(Settings):
    ...     origin: Key[Coordinates] = Key(Coordinates(0, 0))

    >>> settings = MySettings()
    >>> print(repr(settings.origin))
    <Key[Coordinates]:(0,0)>


Note also that in the latter case, :meth:`~sunset.Serializable.fromStr()` must be a
class method.

Both approaches to providing serialization and deserialization methods for your custom
types are valid. :class:`~sunset.Serializer` requires a more verbose instantiation for
your Keys, but allows for the concern of serialization to be kept separate from your
custom type. If you don't care either way, use :class:`~sunset.Serializer`.


Using settings
--------------

Overview
~~~~~~~~

- Instantiate your Settings class during your application's startup.

  .. note::

        Creating multiple instances of your Settings is possible, but individual
        instances will not share values.

- Load your settings from a file with :meth:`~sunset.Settings.load()`. See :ref:`loading
  and saving`.

- Pass down the relevant Settings, Bunch or Key instances to the code locations that
  will update the Keys from user actions and the code locations that will make use of the
  Keys' values.

  .. note::

        Grouping Keys into Bunches allows you to pass only the relevant Keys to the
        parts of your program that use them. This helps prevent the introduction of
        tight coupling between the individual parts of your program.

- Update a Key's value with :meth:`~sunset.Key.set()`, retrieve a Key's current
  value with :meth:`~sunset.Key.get()`. Clear a Key's value with
  :meth:`~sunset.Key.clear()`. When a Key's value is not set,
  :meth:`~sunset.Key.get()` will return that of the next layer up if there is
  one (see :ref:`layering`), else the default value for this Key.

- Add callbacks to take action when a Key's value changes with the
  :meth:`~sunset.Key.onValueChangeCall()` method. Add callbacks to take action when a
  Settings, Bunch or Key is updated in any way with their respective
  :meth:`~sunset.Key.onUpdateCall()` methods.

- Load your settings on start, and save them back to a file when they are
  updated or when your application shuts down. See :ref:`loading and saving`.


.. _layering:

Layering
~~~~~~~~

Layers
......

Your application may need to override settings per user, per folder, etc. In
SunsetSettings, this is done by adding layers using the
:meth:`~sunset.Settings.addLayer()` method. This method creates a new instance
of your Settings on top of the parent instance which can hold its own values.
Where not overridden, the Keys in this layer pass through the values from the
corresponding Keys on the parent layer.

Layers can be given a name, either at creation time or after the fact by calling the
:meth:`~sunset.Settings.setLayerName()` method. This name will be used the generate
a section heading for the layer when saving your Settings to a file.

Layers without a name are not saved. The toplevel layer is named `main` by
default, and cannot be unnamed.

Layer names get normalized to lower case and alphanumeric characters, so for instance
`The Roaring 20s!` would become `theroaring20s`. Names are also unique; if a Settings
instance already holds a layer with a given name, and a new layer is created on that
instance using the same name, then a numeric suffix is appended to that name to make it
unique.

The :meth:`~sunset.Settings.layerName()` method returns the layer's current,
normalized, unique name.

The hierarchy of layers can be arbitrarily deep.

Example:

.. code-block:: python

    >>> from sunset import Key, Settings

    >>> class BackupSettings(Settings):
    ...     path: Key[str]         = Key(default="/")
    ...     destination: Key[str]  = Key(default="/")
    ...     compression: Key[bool] = Key(default=False)

    >>> settings = BackupSettings()
    >>> settings.compression.set(True)
    True

    >>> user1_layer = settings.addLayer("User 1")
    >>> user1_layer.path.set("/home/user1/")
    True
    >>> user1_layer.destination.set("/var/backups/user1/")
    True

    >>> user1_videos_layer = user1_layer.addLayer("Videos")
    >>> user1_videos_layer.path.set("/home/user1/Videos/")
    True
    >>> user1_videos_layer.compression.set(False)
    True

    >>> mails_layer = settings.addLayer("Mails")
    >>> mails_layer.path.set("/var/mail/")
    True
    >>> mails_layer.destination.set("/var/backups/mails/")
    True

Here is what these Settings would look like when saved to a file:

.. code-block:: python

    >>> import io
    >>> text = io.StringIO()
    >>> settings.save(text)
    >>> print(text.getvalue(), end="")
    [main]
    compression = true
    [mails]
    destination = /var/backups/mails/
    path = /var/mail/
    [user1]
    destination = /var/backups/user1/
    path = /home/user1/
    [user1/videos]
    compression = false
    path = /home/user1/Videos/


Bunches, Lists and Keys
.......................

When you create a new layer on your Settings, the Keys in that layer and in its
Bunches are automatically set up to use the corresponding Keys in the parent
layer as their default values.

A List's behavior does not change in a layer except for the
:meth:`~sunset.List.iter()` method. This method return an iterable on the List's
items and optionally its parent layer's items. An optional parameter indicates
if the parent's items will be returned, and if so, whether they will be returned
before or after this List's items. The default value for this parameter for a
given List can be set on that List at creation time.

Example:

.. code-block:: python

    >>> from sunset import Key, List, Settings

    >>> class BackupSettings(Settings):
    ...     path: Key[str] = Key(default="/")
    ...     ignore_patterns: List[Key[str]] = List(
    ...         Key(default="*"), order=List.PARENT_FIRST
    ...     )

    >>> settings = BackupSettings()

    >>> user1_layer = settings.addLayer("User 1")
    >>> user1_layer.path.set("/home/user1/")
    True
    >>> user1_layer.ignore_patterns.appendOne().set("*.tmp")
    True

    >>> user1_code_layer = user1_layer.addLayer("Code")
    >>> user1_code_layer.path.set("/home/user1/Code/Python/")
    True
    >>> user1_code_layer.ignore_patterns.appendOne().set("*.py")
    True
    >>> user1_code_layer.ignore_patterns.appendOne().set("__pycache__")
    True

    >>> print([
    ...     pattern.get() for pattern in user1_code_layer.ignore_patterns.iter()
    ... ])
    ['*.tmp', '*.py', '__pycache__']


.. _loading and saving:

Loading and saving settings
---------------------------

Load settings from an open text-mode file object with :meth:`~sunset.Settings.load()`.
Save settings to an open, writable text-mode file object with
:meth:`~sunset.Settings.save()`.

Alternatively, use either the :class:`~sunset.AutoSaver` or the
:class:`~sunset.AutoLoader` context manager to automatically load and save your
settings.

Which one you should use depends on how your users are expected to update settings: if
that's by editing the settings file, to be loaded into your application, then use
:class:`~sunset.AutoLoader`; if that's by making changes in the application's user
interface, to be saved into the settings file, then use :class:`~sunset.AutoSaver`.

Note that :class:`~sunset.AutoLoader` automatically reloads your application's settings
when the settings file is modified, and :class:`~sunset.AutoSaver` automatically saves
them when they are updated from inside your application.

SunsetSettings uses an INI-like file format to store settings. This format is intended
to be easy for humans to make sense of.

It is however somewhat limited at this time. In particular, it does not support comments.

Saving settings does not preserve formatting.

.. note::

    Because the :meth:`~sunset.Settings.load()` and :meth:`~sunset.Settings.save()`
    methods take an already open text file object as their argument, those methods don't
    get a say in which encoding the target file will use. Be sure to open the file using
    an encoding capable of holding any character that can be used in a setting by the
    users of your application. If in doubt, use `UTF-8`.