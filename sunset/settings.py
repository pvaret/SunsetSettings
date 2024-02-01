import logging
import pathlib

from typing import (
    Any,
    Callable,
    IO,
    Iterator,
    MutableSet,
    Optional,
    TypeVar,
    Union,
)

from .autosaver import AutoSaver
from .bunch import Bunch
from .exporter import normalize, load_from_file, save_to_file
from .lockable import Lockable
from .non_hashable_set import NonHashableSet
from .protocols import UpdateNotifier

_MAIN = "main"


# TODO: Replace with typing.Self when mypy finally supports that.
Self = TypeVar("Self", bound="Settings")


class Settings(Bunch, Lockable):
    """
    A collection of keys that can be saved to and loaded from text, and supports
    subsections.

    Under the hood, a Settings class is a dataclass, and can be used in the same
    manner, i.e. by defining attributes directly on the class itself.

    Settings instances support subsections: calling the :meth:`newSection()`
    method on an instance creates a subsection of that instance. This subsection
    holds the same keys, with independant values. If a key of the subsection
    does not have a value, its value will be looked up on its parent section
    instead. The hierarchy of sections can be arbitrarily deep.

    When saving a Settings instance, its subsections are saved with it under a
    distinct heading for each, provided they have a name. A section is given a
    name by passing it to the :meth:`newSection()` method, or by using the
    :meth:`setSectionName()` method on the new section after creation.

    The name of each section is used to construct the heading it is saved under.
    The top-level Settings instance is saved under the `[main]` heading by
    default.

    Anonymous (unnamed) sections do not get saved.

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
    >>> mammals = animals.newSection(name="mammals")
    >>> mammals.fur.set(True)
    True
    >>> mammals.legs.set(4)
    True
    >>> humans = mammals.newSection(name="humans")
    >>> humans.legs.set(2)
    True
    >>> humans.fur.set(False)
    True
    >>> birds = animals.newSection(name="birds")
    >>> birds.legs.set(2)
    True
    >>> birds.wings.set(2)
    True
    >>> aliens = animals.newSection()  # No name given!
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

    _SECTION_SEPARATOR = "/"

    _section_name: str = ""
    _children_set: MutableSet[Bunch]
    _autosaver: Optional[AutoSaver] = None
    _autosaver_class: type[AutoSaver]

    def __post_init__(self) -> None:
        super().__post_init__()

        # Note that this overrides the similarly named attribute from the parent
        # class. In the parent class, the set does not keep references to its
        # items; in this class, it does.

        self._children_set = NonHashableSet()
        self._autosaver_class = AutoSaver

    @Lockable.with_lock
    def newSection(self: Self, name: str = "") -> Self:
        """
        Creates and returns a new instance of this class. Each key of the new
        instance will inherit from the key of the same name on the parent
        instance.

        When saving Settings with the :meth:`save()` method, each section's name
        is used to generate the heading under which that section is saved. If
        the new section is created without a name, it will be skipped when
        saving. A name can still be given to a section after creation with the
        :meth:`setSectionName()` method.

        If this Settings instance already has a section with the given name, the
        new section will be created with a unique name generated by appending a
        numbered suffix to that name.

        Args:
            name: The name that will be used to generate a heading for this
                section when saving it to text. The given name will be
                normalized to lowercase alphanumeric characters.

        Returns:
            An instance of the same type as self.
        """

        new = self._newInstance()
        new.setSectionName(name)

        # Note that this will trigger an update notification.

        new.setParent(self)

        return new

    @Lockable.with_lock
    def getOrCreateSection(self: Self, name: str) -> Self:
        """
        Finds and returns the section of these Settings with the given name if
        it exists, and creates it if it doesn't.

        If the given name is empty, this is equivalent to calling
        :meth:`newSection()` instead.

        Args:
            name: The name that will be used to generate a heading for this
                section when saving it to text. The given name will be
                normalized to lowercase alphanumeric characters.

        Returns:
            An instance of the same type as self.
        """

        return (
            section
            if (section := self.getSection(name)) is not None
            else self.newSection(name=name)
        )

    def getSection(self: Self, name: str) -> Optional[Self]:
        """
        Finds and returns a section of this instance with the given name, if it
        exists, else None.

        Args:
            name: The name of the section to return.

        Returns:
            An instance of the same type as self, or None.
        """

        norm = normalize(name)
        if not norm:
            return None

        for section in self.sections():
            if norm == section.sectionName():
                return section

        return None

    def sections(self: Self) -> Iterator[Self]:
        """
        Returns an iterator over the subsections of this Settings instance. Note
        that the subsections are only looked up one level deep, that is to say,
        no recursing into the section hierarchy occurs.

        Returns:
            An iterator over Settings instances of the same type as this one.
        """

        yield from sorted(self.children())

    def setSectionName(self, name: str) -> str:
        """
        Sets the unique name under which this Settings instance will be
        persisted by the :meth:`save()` method. The given name will be
        normalized to lowercase, without space or punctuation.

        This name is guaranteed to be unique. If the given name is already used
        by a section of the same Settings instance, then a numbered suffix is
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
        >>> section1 = parent.newSection()
        >>> section2 = parent.newSection()
        >>> section3 = parent.newSection()
        >>> section1.setSectionName("  T ' e ? S / t")
        'test'
        >>> section2.setSectionName("TEST")
        'test_1'
        >>> section3.setSectionName("test")
        'test_2'
        >>> # This should not change this section's name.
        >>> section3.setSectionName("test")
        'test_2'
        """

        name = normalize(name)

        if (parent := self.parent()) is None:
            if name != self._section_name:
                self._section_name = name
                self._triggerUpdateNotification(self)

        else:
            # Note that this triggers a notification if the unique name is
            # different from the current name.

            parent._setUniqueNameForSection(name, self)

        return self.sectionName()

    @Lockable.with_lock
    def _setUniqueNameForSection(self: Self, name: str, section: Self) -> None:
        candidate = name = normalize(name)

        if candidate:
            other_names = set(
                s.sectionName() for s in self.children() if s is not section
            )

            i = 0
            while candidate in other_names:
                i += 1
                candidate = f"{name}_{i}"

        if candidate != section._section_name:
            section._section_name = candidate
            section._triggerUpdateNotification(section)

    def sectionName(self) -> str:
        """
        Returns the current name of this Settings instance. This name will be
        used to generate the heading under which this Settings instance will be
        persisted by the :meth:`save()` method.

        Returns:
            The name of this Settings instance.
        """
        if name := self._section_name:
            return name

        return name if self.parent() is not None else self.MAIN

    @Lockable.with_lock
    def setParent(self: Self, parent: Optional[Self]) -> None:  # type: ignore
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

        Returns:
            None.
        """

        if parent is (previous_parent := self.parent()):
            return

        # Ensure that this section's name is unique in its parent.

        if parent is not None:
            # May trigger an update notification if the name is changed.

            parent._setUniqueNameForSection(self._section_name, self)

        super().setParent(parent)  # type:ignore

        if parent is not None:
            parent._triggerUpdateNotification(parent)

        if previous_parent is not None:
            previous_parent._triggerUpdateNotification(previous_parent)

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

        Returns:
            None.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        super().onUpdateCall(callback)

    def _triggerUpdateNotification(
        self, field: Optional[UpdateNotifier]
    ) -> None:
        if not self._update_notification_enabled:
            return

        if field is None:
            field = self

        super()._triggerUpdateNotification(field)

        if (parent := self.parent()) is not None:
            parent._triggerUpdateNotification(field)

    def skipOnSave(self) -> bool:
        return self.sectionName() == ""

    def dumpFields(self) -> Iterator[tuple[str, Optional[str]]]:
        """
        Internal.
        """

        if not self.skipOnSave():
            # Ensure the section is dumped event if empty. Dumping an empty
            # section is valid.

            label = (self.sectionName() or "?") + self._SECTION_SEPARATOR

            if not self.isSet():
                yield label, None
            else:
                yield from (
                    (label + path, item) for path, item in super().dumpFields()
                )

            for section in self.sections():
                yield from (
                    (label + path, item) for path, item in section.dumpFields()
                )

    def restoreField(self, path: str, value: Optional[str]) -> bool:
        """
        Internal.
        """

        if self._SECTION_SEPARATOR not in path:
            return False

        section_name, path = path.split(self._SECTION_SEPARATOR, 1)
        if self.sectionName() != section_name:
            return False

        success: bool = False

        _update_notification_enabled = self._update_notification_enabled
        self._update_notification_enabled = False

        if self._SECTION_SEPARATOR in path:
            subsection_name, _ = path.split(self._SECTION_SEPARATOR, 1)
            if subsection_name:
                section = self.getOrCreateSection(subsection_name)
                success = section.restoreField(path, value)

        else:
            success = super().restoreField(path, value)

        self._update_notification_enabled = _update_notification_enabled

        return success

    def save(self, file: IO[str], blanklines: bool = False) -> None:
        """
        Writes the contents of this Settings instance and its subsections in
        text form to the given file object.

        Args:
            file: A text file object where to save this Settings instance.

            blanklines: Whether to add a blank line before section headings.

        Returns:
            None.
        """

        if self.skipOnSave():
            # This is an anonymous instance, actually. There is therefore
            # nothing to save.

            return

        save_to_file(file, self.dumpFields(), blanklines=blanklines)

    def load(self, file: IO[str]) -> None:
        """
        Loads settings from the given text file object.

        If the given file contains lines that don't make sense -- for instance,
        if the line is garbage, or refers to a key that does not exist in this
        Settings class, or it exists but with an incompatible type -- then the
        faulty line is skipped silently.

        If the text file object contains multiple headings, those headings will
        be used to create subsections with the corresponding names.

        Loading settings from a file does not reset the existing settings or
        sections. Which means you can split your configuration into multiple
        files if needed and load each file in turn to reconstruct the full
        settings.

        Args:
            file: A text file open in reading mode.

        Returns:
            None.
        """

        for path, dump in load_from_file(file, self.sectionName()):
            self.restoreField(path, dump)

    def setAutosaverClass(self, class_: type[AutoSaver]) -> None:
        """
        Internal.
        """
        self._autosaver_class = class_

    def autosave(
        self,
        path: Union[str, pathlib.Path],
        save_on_update: bool = True,
        save_delay: int = 0,
        logger: Optional[logging.Logger] = None,
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
            logger=logger,
        )
        return self._autosaver

    def __lt__(self: Self, other: Self) -> bool:
        # Giving sections an order lets us easily sort them when dumping.

        return self.sectionName() < other.sectionName()
