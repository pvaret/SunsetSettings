import logging
import sys
from collections.abc import Callable, Iterable, MutableSet
from functools import wraps
from pathlib import Path
from typing import IO, Any, ParamSpec, TypeVar

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Self
else:
    from typing import Self

if sys.version_info < (3, 13):
    import warnings

    _P = ParamSpec("_P")
    _T = TypeVar("_T")

    def deprecated(msg: str) -> Callable[[Callable[_P, _T]], Callable[_P, _T]]:
        def wrap(func: Callable[_P, _T]) -> Callable[_P, _T]:
            @wraps(func)
            def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _T:
                warnings.warn(msg, DeprecationWarning, stacklevel=2)
                return func(*args, **kwargs)

            return wrapped

        return wrap

else:
    from warnings import deprecated

from sunset.autosaver import AutoSaver
from sunset.bunch import Bunch
from sunset.exporter import load_from_file, normalize, save_to_file
from sunset.lock import SettingsLock
from sunset.sets import NonHashableSet
from sunset.stringutils import collate_by_prefix, split_on

_MAIN = "main"

_FieldItemT = tuple[str, str | None]


class Settings(Bunch):
    """
    A layerable collection of configuration keys.

    Under the hood, a Settings class is a dataclass, and can be used in the same
    manner, i.e. by defining attributes directly on the class itself.

    Settings instances support layers: calling the :meth:`addLayer()` method on
    an instance creates a layer on top of that instance. This layer holds the
    same keys, with their own values. If a key on a layer does not have a value
    of its own, it will use its parent layer's value instead. The stack of
    layers can be arbitrarily deep.

    When saving a Settings instance, its layers are saved with it under a
    distinct heading for each, provided they have a name. A layer is given a
    name by passing it to the :meth:`addLayer()` method, or by using the
    :meth:`setLayerName()` method on the new layer after creation.

    The name of each layer is used to construct the heading it is saved under.
    The top-level Settings instance is saved under the `[main]` heading by
    default.

    Anonymous (unnamed) layers do not get saved.

    Example:

    >>> from sunset import Key, Settings
    >>> class AnimalSettings(Settings):
    ...     hearts: Key[int] = Key(default=0)
    ...     legs: Key[int]   = Key(default=0)
    ...     wings: Key[int]  = Key(default=0)
    ...     fur: Key[bool]   = Key(default=False)
    >>> animals = AnimalSettings()
    >>> animals.hearts.set(1)
    True
    >>> mammals = animals.addLayer(name="mammals")
    >>> mammals.fur.set(True)
    True
    >>> mammals.legs.set(4)
    True
    >>> humans = mammals.addLayer(name="humans")
    >>> humans.legs.set(2)
    True
    >>> humans.fur.set(False)
    True
    >>> birds = animals.addLayer(name="birds")
    >>> birds.legs.set(2)
    True
    >>> birds.wings.set(2)
    True
    >>> aliens = animals.addLayer()  # No name given!
    >>> aliens.hearts.set(2)
    True
    >>> aliens.legs.set(7)
    True
    >>> print(mammals.hearts.get())
    1
    >>> print(mammals.legs.get())
    4
    >>> print(mammals.wings.get())
    0
    >>> print(mammals.fur.get())
    True
    >>> print(birds.hearts.get())
    1
    >>> print(birds.legs.get())
    2
    >>> print(birds.wings.get())
    2
    >>> print(birds.fur.get())
    False
    >>> print(humans.hearts.get())
    1
    >>> print(humans.legs.get())
    2
    >>> print(humans.wings.get())
    0
    >>> print(humans.fur.get())
    False
    >>> print(aliens.hearts.get())
    2
    >>> print(aliens.legs.get())
    7
    >>> print(aliens.wings.get())
    0
    >>> print(aliens.fur.get())
    False
    >>> import io
    >>> txt = io.StringIO()
    >>> animals.save(txt)
    >>> print(txt.getvalue(), end="")
    [main]
    hearts = 1
    [birds]
    legs = 2
    wings = 2
    [mammals]
    fur = true
    legs = 4
    [mammals/humans]
    fur = false
    legs = 2
    """

    MAIN: str = _MAIN

    _LAYER_SEPARATOR = "/"

    _layer_name: str = ""
    _children_set: MutableSet[Bunch]
    _autosaver: AutoSaver | None = None
    _autosaver_class: type[AutoSaver]

    def __init__(self) -> None:
        super().__init__()

        # Note that this overrides the similarly named attribute from the parent
        # class. In the parent class, the set does not keep references to its
        # items; in this class, it does.

        self._children_set = NonHashableSet()
        self._autosaver_class = AutoSaver

    @SettingsLock.with_write_lock
    def addLayer(self, name: str = "") -> Self:
        """
        Creates and returns a new instance of this class. Each key of the new
        instance will inherit from the key of the same name on the parent
        instance.

        When saving Settings with the :meth:`save()` method, each layer's name
        is used to generate the heading under which that layer is saved. If
        the new layer is created without a name, it will be skipped when
        saving. A name can still be given to a layer after creation with the
        :meth:`setLayerName()` method.

        If this Settings instance already has a layer with the given name, the
        new layer will be created with a unique name generated by appending a
        numbered suffix to that name.

        Args:
            name: The name that will be used to generate a heading for this
                layer when saving it to text. The given name will be
                normalized to lowercase alphanumeric characters.

        Returns:
            An instance of the same type as self.
        """

        new = self._newInstance()
        new.setLayerName(name)

        # Note that this will trigger an update notification.

        new.setParent(self)

        return new

    @deprecated("Use 'addLayer()' instead.")
    def newSection(self, name: str = "") -> Self:
        return self.addLayer(name)

    @SettingsLock.with_write_lock
    def getOrAddLayer(self, name: str) -> Self:
        """
        Finds and returns the layer of these Settings with the given name if
        it exists, and creates it if it doesn't.

        If the given name is empty, this is equivalent to calling
        :meth:`addLayer()` instead.

        Args:
            name: The name that will be used to generate a heading for this
                layer when saving it to text. The given name will be
                normalized to lowercase alphanumeric characters.

        Returns:
            An instance of the same type as self.
        """

        return (
            layer
            if (layer := self.getLayer(name)) is not None
            else self.addLayer(name=name)
        )

    @deprecated("Use 'getOrAddLayer()' instead.")
    def getOrCreateSection(self, name: str) -> Self:
        return self.getOrAddLayer(name)

    @SettingsLock.with_read_lock
    def getLayer(self, name: str) -> Self | None:
        """
        Finds and returns a layer of this instance with the given name, if it
        exists, else None.

        Args:
            name: The name of the layer to return.

        Returns:
            An instance of the same type as self, or None.
        """

        norm = normalize(name)
        if not norm:
            return None

        for layer in self.layers():
            if norm == layer.layerName():
                return layer

        return None

    @deprecated("Use 'getLayer()' instead.")
    def getSection(self, name: str) -> Self | None:
        return self.getLayer(name)

    @SettingsLock.with_read_lock
    def layers(self) -> Iterable[Self]:
        """
        Returns an iterable with the layers of this Settings instance. Note that
        the layers are only looked up one level deep, that is to say, no recursing
        into the layer hierarchy occurs.

        Returns:
            An iterable of Settings instances of the same type as this one.
        """

        return sorted(self.children())

    @deprecated("Use 'layers()' instead.")
    def sections(self) -> Iterable[Self]:
        return self.layers()

    @SettingsLock.with_write_lock
    def setLayerName(self, name: str) -> str:
        """
        Sets the unique name under which this Settings layer will be persisted
        by the :meth:`save()` method. The given name will be normalized to
        lowercase, without space or punctuation.

        This name is guaranteed to be unique. If the given name is already used
        by a layer of the same Settings instance, then a numbered suffix is
        generated to make this one's name unique.

        If the given name is empty, these settings will be skipped when saving.

        The toplevel Settings instance is named "main" by default. It cannot be
        unnamed; it will revert to its default name instead.

        Args:
            name: The name that will be used to generate a heading for these
                settings when saving them to text.

        Returns:
            The given name, normalized, and made unique if needed.

        Example:

        >>> from sunset import Settings
        >>> class TestSettings(Settings):
        ...     pass
        >>> parent = TestSettings()
        >>> layer1 = parent.addLayer()
        >>> layer2 = parent.addLayer()
        >>> layer3 = parent.addLayer()
        >>> layer1.setLayerName("  T ' e ? S / t")
        'test'
        >>> layer2.setLayerName("TEST")
        'test_1'
        >>> layer3.setLayerName("test")
        'test_2'
        >>> # This should not change this layer's name.
        >>> layer3.setLayerName("test")
        'test_2'
        """

        name = normalize(name)

        if (parent := self.parent()) is None:
            if name != self._layer_name:
                self._layer_name = name
                self._update_notifier.trigger(self)

        else:
            # Note that this triggers a notification if the unique name is
            # different from the current name.

            parent._setUniqueNameForLayer(name, self)  # noqa: SLF001

        return self.layerName()

    @deprecated("Use 'setLayerName()' instead.")
    def setSectionName(self, name: str) -> str:
        return self.setLayerName(name)

    def _setUniqueNameForLayer(self, name: str, layer: Self) -> None:
        candidate = name = normalize(name)

        if candidate:
            other_names = {s.layerName() for s in self.children() if s is not layer}

            i = 0
            while candidate in other_names:
                i += 1
                candidate = f"{name}_{i}"

        if candidate != layer._layer_name:  # noqa: SLF001
            layer._layer_name = candidate  # noqa: SLF001
            layer._update_notifier.trigger(layer)  # noqa: SLF001

    @SettingsLock.with_read_lock
    def layerName(self) -> str:
        """
        Returns the current name of this Settings instance. This name will be
        used to generate the heading under which this Settings instance will be
        persisted by the :meth:`save()` method.

        Returns:
            The name of this Settings instance.
        """
        if name := self._layer_name:
            return name

        return name if self.parent() is not None else self.MAIN

    @deprecated("Use 'layerName()' instead.")
    def sectionName(self) -> str:
        return self.layerName()

    @SettingsLock.with_write_lock
    def setParent(self, parent: Self | None) -> None:
        """
        Makes the given Settings instance the parent of this one. If None,
        remove this instance's parent, if any.

        All the Key, List and Bunch fields defined on this instance will be
        recursively reparented to the corresponding Key / List / Bunch field on
        the given parent.

        This method is for internal purposes and you will typically not need to
        call it directly.

        Args:
            parent: Either a Settings instance that will become this instance's
                parent, or None. The parent Settings instance must have the same
                type as this instance.
        """

        if parent is (previous_parent := self.parent()):
            return

        # Ensure that this layer's name is unique in its parent.

        if parent is not None:
            # May trigger an update notification if the name is changed.

            parent._setUniqueNameForLayer(self._layer_name, self)  # noqa: SLF001
            self._update_notifier.add(parent._update_notifier.trigger)  # noqa: SLF001

        super().setParent(parent)

        if parent is not None:
            parent._update_notifier.trigger(parent)  # noqa: SLF001

        if previous_parent is not None:
            previous_parent._update_notifier.trigger(previous_parent)  # noqa: SLF001
            self._update_notifier.discard(previous_parent._update_notifier.trigger)  # noqa: SLF001

    # Not actually useless. This lets us override the docstring with
    # Settings-specific info.
    # pylint: disable-next=useless-parent-delegation
    def onUpdateCall(self, callback: Callable[[Any], Any]) -> None:
        """
        Adds a callback to be called whenever this Settings instance is updated.
        A Settings instance is considered updated when any of its fields is
        updated, or when its name is updated.

        The callback will be called with as its argument whichever field was
        just updated.

        Args:
            callback: A callable that will be called with one argument of type
                :class:`~sunset.List`, :class:`~sunset.Bunch` or
                :class:`~sunset.Key`.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        super().onUpdateCall(callback)

    def skipOnSave(self) -> bool:
        return self.layerName() == ""

    @SettingsLock.with_read_lock
    def dumpFields(self) -> Iterable[tuple[str, str | None]]:
        """
        Internal.
        """

        ret: list[tuple[str, str | None]] = []
        if not self.skipOnSave():
            # Ensure the layer is dumped even if empty. Dumping an empty layer is
            # valid.

            if not self.isSet():
                ret.append(("", None))
            else:
                ret.extend((path, item) for path, item in super().dumpFields())

            for layer in self.layers():
                ret.extend(
                    (layer.layerName() + self._LAYER_SEPARATOR + path, item)
                    for path, item in layer.dumpFields()
                )

        return ret

    @SettingsLock.with_write_lock
    def restoreFields(self, fields: Iterable[_FieldItemT]) -> bool:
        """
        Internal.
        """

        previous_layers = {layer.layerName(): layer for layer in self.layers()}

        fields = list(fields)

        sep = self._LAYER_SEPARATOR
        bunch_fields = [(path, value) for path, value in fields if sep not in path]
        by_layer = collate_by_prefix(
            [(path, value) for path, value in fields if sep in path],
            split_on(sep),
        )

        with self._update_notifier.inhibit():
            any_change = super().restoreFields(bunch_fields)

            for layer_name, layer in previous_layers.items():
                if layer_name not in by_layer:
                    layer.setParent(None)
                    layer.clear()
                    any_change = True
                    continue

                any_change = layer.restoreFields(by_layer.pop(layer_name)) or any_change

            for layer_name, layer_fields in by_layer.items():
                if not layer_name:
                    continue
                layer = self.getOrAddLayer(layer_name)
                any_change = layer.restoreFields(layer_fields) or any_change

        return any_change

    def save(self, file: IO[str] | str | Path, *, blanklines: bool = False) -> None:
        """
        Writes the contents of this Settings instance and its layers in text
        form to the given file.

        Args:
            file: The file where to save these Settings.

            blanklines: Whether to add a blank line before layer headings.
        """

        if self.skipOnSave():
            # This is an anonymous instance, actually. There is therefore
            # nothing to save.

            return

        if isinstance(file, str):
            file = Path(file)

        if isinstance(file, Path):
            file = file.open("w", encoding="UTF-8")

        save_to_file(
            file, self.dumpFields(), blanklines=blanklines, main=self.layerName()
        )

    def load(self, file: IO[str] | str | Path) -> None:
        """
        Loads settings from the given file.

        If the given file contains lines that don't make sense -- for instance,
        if the line is garbage, or refers to a key that does not exist in this
        Settings class, or it exists but with an incompatible type -- then the
        faulty line is skipped silently.

        If the file contains multiple headings, those headings will be used to
        create layers with the corresponding names.

        Note that loading new settings resets the current settings.

        Args:
            file: The file to load.
        """

        if isinstance(file, str):
            file = Path(file)

        if isinstance(file, Path):
            file = file.open(encoding="UTF-8")

        self.restoreFields(load_from_file(file, self.layerName()))

    def autosave(
        self,
        path: str | Path,
        *,
        save_on_update: bool = True,
        save_delay: int = 0,
        raise_on_error: bool = False,
        logger: logging.Logger | None = None,
    ) -> AutoSaver:
        """
        Returns a context manager that loads these Settings from the given file
        path on instantiation and saves them on exit.

        By default, it will also automatically save the settings whenever they
        are updated from inside the application. Optionally, the updates can be
        batched over a given delay before being saved.

        See the documentation of :class:`~sunset.AutoSaver` for the details.

        Args:
            path: The full path to the file to load the settings from and save
                them to. If this file does not exist yet, it will be created
                when saving for the first time.

            save_on_update: Whether to save the settings when they
                are updated in any way. Default: True.

            save_delay: How long to wait, in seconds, before actually saving the
                settings when `save_on_update` is True and an update occurs.
                Setting this to a few seconds will batch updates for that long
                before triggering a save. If set to 0, the save is triggered
                immediately. Default: 0.

            raise_on_error: Whether OS errors occurring while loading and saving the
                settings should raise an exception. If False, errors will only be
                logged. Default: False.

            logger: A logger instance that will be used to log OS errors, if
                any, while loading or saving settings. If none is given, the
                default root logger will be used.

        Returns:
            An AutoSaver context manager.
        """

        # Keep a reference to the AutoSaver instance, so that its lifetime is
        # bound to that of this Settings instance.

        self._autosaver = self._autosaver_class(
            self,
            path,
            save_on_update=save_on_update,
            save_delay=save_delay,
            raise_on_error=raise_on_error,
            logger=logger,
        )
        return self._autosaver

    def __lt__(self, other: Self) -> bool:
        # Giving layers an order lets us easily sort them when dumping.

        return self.layerName() < other.layerName()
