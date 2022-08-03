from typing import MutableSet, Sequence, TextIO, cast

from typing_extensions import Self

from .exporter import normalize, loadFromFile, saveToFile
from .non_hashable_set import NonHashableSet
from .protocols import ModificationNotifier
from .section import Section

_MAIN = "main"


class Settings(Section):
    """
    A collection of settings that can be saved to and loaded from text, and
    supports inheritance.

    Under the hood, a Settings class is a dataclass, and can be used in the same
    manner, i.e. by defining attributes directly on the class itself.

    Settings instances support inheritance: calling the `derive()` or
    `deriveAs()` method on an instance creates a child of that instance; when a
    setting has not been set on the child, the value of that setting is looked
    up on its parent instead. The hierarchy of children can be arbitrarily
    deep.

    When saving a Settings instance, its children are saved with it under a
    distinct heading for each, provided they have a name. Children are given a
    name by using the `deriveAs()` method instead of `derive()` to create them,
    or by using the `setName()` method after creation.

    Anonymous (unnamed) children do not get saved. The name of each child is
    used to construct the heading it is saved under. The top-level Settings
    instance is saved under the '[main]' heading.

    Example:

    >>> import sunset

    >>> class AnimalSettings(sunset.Settings):
    ...     hearts: sunset.Setting[int] = sunset.NewSetting(default=0)
    ...     legs: sunset.Setting[int] = sunset.NewSetting(default=0)
    ...     wings: sunset.Setting[int] = sunset.NewSetting(default=0)
    ...     fur: sunset.Setting[bool] = sunset.NewSetting(default=False)

    >>> animals = AnimalSettings()
    >>> animals.hearts.set(1)

    >>> mammals = animals.deriveAs("mammals")
    >>> mammals.fur.set(True)
    >>> mammals.legs.set(4)

    >>> humans = mammals.deriveAs("humans")
    >>> humans.legs.set(2)
    >>> humans.fur.set(False)

    >>> birds = animals.deriveAs("birds")
    >>> birds.legs.set(2)
    >>> birds.wings.set(2)

    >>> aliens = animals.derive()  # No name given!
    >>> aliens.hearts.set(2)
    >>> aliens.legs.set(7)

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
    >>> print(txt.getvalue(), end='')
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

    _name: str
    _children: MutableSet[Self]

    def __post_init__(self) -> None:

        super().__post_init__()

        self._name = ""
        self._children = NonHashableSet()

    def derive(self: Self) -> Self:
        """
        Creates and returns a new instance of this class. Each setting of the
        new instance will inherit from the setting of the same name on this
        instance.

        The new instance is created without a name, and will be skipped by the
        `save()` method. A name can be given to it after the fact with the
        `setName()` method.

        Returns:
            An instance of the same type as self.
        """

        new = cast(Self, super().derive())
        new.onSettingModifiedCall(self._notifyModification)

        return new

    def deriveAs(self: Self, name: str) -> Self:
        """
        Creates or finds and returns a new instance of this class with the given
        name. Each setting of the new instance will inherit from the setting of
        the same name on this instance.

        The new instance is created with, or looked up using, the given name.
        If the given name is empty, this is equivalent to calling `derive()`
        instead.

        Args:
            name: The name that will be used to generate a heading for these
                settings when saving them to text.

        Returns:
            An instance of the same type as self.
        """

        norm = normalize(name)

        if not norm:
            return self.derive()

        for child in self.children():
            if norm == child.name():
                return child

        new = self.derive()
        new.setName(name)

        return new

    def setName(self, name: str) -> str:
        """
        Sets the name under which this Settings instance will be persisted by
        the `save()` method. The given name will be normalized to lowercase,
        without space or punctuation.

        If the given name is empty, these settings will be skipped when saving.

        The toplevel Settings instance is named "main" by default. It cannot be
        unnamed; it will revert to its default name instead.

        Args:
            name: The name that will be used to generate a heading for these
                settings when saving them to text.

        Returns:
            The given name, normalized.
        """

        name = normalize(name)
        previous_name = self.name()

        self._name = name

        if self.name() != previous_name:
            self._notifyModification(self)

        return self.name()

    def name(self) -> str:
        """
        Returns the current name of this Settings instance. This name will be
        used to generate the heading under which this Settings instance will be
        persisted by the `save()` method.

        Returns:
            The name of this Settings instance.
        """
        if self._name:
            return self._name

        return self._name if self.parent() is not None else self.MAIN

    def hierarchy(self) -> list[str]:
        """
        Internal.
        """

        if not self.name():
            return []

        parent = self.parent()
        if parent is not None and not parent.hierarchy():
            return []

        return (parent.hierarchy() if parent is not None else []) + [
            self.name()
        ]

    def _notifyModification(self, value: ModificationNotifier) -> None:

        if isinstance(value, Settings) and value.name() == "":
            return

        super()._notifyModification(value)

    def dumpAll(
        self,
    ) -> Sequence[tuple[Sequence[str], Sequence[tuple[str, str]]]]:
        """
        Internal.
        """

        hierarchy = self.hierarchy()
        if not hierarchy:

            # This is an anonymous structure, don't dump it.

            return []

        ret: list[tuple[Sequence[str], Sequence[tuple[str, str]]]] = []
        ret.append((hierarchy, self.dump()))

        children = list(self.children())
        children.sort(key=lambda child: child.name())
        for child in children:
            for hierarchy, dump in child.dumpAll():
                ret.append((hierarchy, dump))

        return ret

    def restoreAll(
        self,
        data: Sequence[tuple[Sequence[str], Sequence[tuple[str, str]]]],
    ) -> None:
        """
        Internal.
        """

        own_children: dict[str, Settings] = {}
        own_children_data: list[
            tuple[Sequence[str], Sequence[tuple[str, str]]]
        ] = []

        for hierarchy, dump in data:

            hierarchy = list(map(normalize, hierarchy))
            if not hierarchy:
                continue

            if not hierarchy[0]:
                continue

            if hierarchy[0] != self.name():
                continue

            if len(hierarchy) == 1:

                # This dump applies specifically to this instance.

                self.restore(dump)

            else:
                child_name = normalize(hierarchy[1])
                if not child_name:
                    continue

                if child_name not in own_children:
                    own_children[child_name] = self.deriveAs(child_name)
                own_children_data.append((hierarchy[1:], dump))

        for child in own_children.values():
            child.restoreAll(own_children_data)

    def save(self, file: TextIO, blanklines: bool = False) -> None:
        """
        Writes the contents of this Settings instance and its children in text
        form to the given file object.

        Args:
            file: A text file object where to save this Settings instance.
            blanklines: Whether to add a blank line before headings.

        Returns:
            None.
        """

        saveToFile(file, self.dumpAll(), self.name(), blanklines=blanklines)

    def load(self, file: TextIO) -> None:
        """
        Loads settings from the given text file object.

        If the given file contains lines that don't make sense -- for instance,
        if the line is garbage, or refers to a setting that does not exist in
        this Settings class, or it exists but with an incompatible type -- then
        the faulty line is skipped silently.

        If the text file object contains multiple headings, those headings will
        be used to create children with the corresponding names.

        Loading settings from a file does not reset the existing settings or
        children. Which means you can split your configuration into multiple
        files if needed.

        Args:
            file: A text file open in reading mode.

        Returns:
            None.
        """

        data = loadFromFile(file, self.name())
        self.restoreAll(data)
