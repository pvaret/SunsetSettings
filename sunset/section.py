import weakref

from dataclasses import dataclass, field
from typing import (
    Callable,
    Iterator,
    MutableSet,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

from typing_extensions import Self

from .non_hashable_set import WeakNonHashableSet
from .protocols import Dumpable, Inheriter, Restorable, ModificationNotifier
from .registry import CallbackRegistry


SectionT = TypeVar("SectionT", bound="Section")


class Section:
    """
    A collection of related settings.

    Under the hood, a Section is a dataclass, and can be used in the same
    manner, i.e. by defining attributes directly on the class itself.

    When adding a Section to a Settings or another Section definition, do not
    instantiate the Section class directly; use the `sunset.NewSection()`
    function instead.

    Example:

    >>> import sunset
    >>> class MySection(sunset.Section):
    ...     class MySubsection(sunset.Section):
    ...         subsetting: sunset.Setting[int] = sunset.NewSetting(default=0)
    ...
    ...     subsection1: MySubsection = sunset.NewSection(MySubsection)
    ...     subsection2: MySubsection = sunset.NewSection(MySubsection)

    >>> section = MySection()
    >>> section.subsection1.subsetting.get()
    0
    >>> section.subsection2.subsetting.get()
    0
    >>> section.subsection1.subsetting.set(42)
    >>> section.subsection2.subsetting.set(101)
    >>> section.subsection1.subsetting.get()
    42
    >>> section.subsection2.subsetting.get()
    101
    """

    _parent: Optional[weakref.ref[Self]]
    _children: MutableSet[Self]
    _modification_notification_callbacks: CallbackRegistry[Self]

    def __new__(cls: Type[Self]) -> Self:

        # This is a non-top-level import in order to avoid a circular
        # dependency.

        from . import section_validation

        # Potentially raises ValueError if the user is holding it wrong.

        section_validation.validateElementsAreFields(cls)

        wrapped = dataclass()(cls)
        return super().__new__(wrapped)

    def __post_init__(self: Self) -> None:

        self._parent = None
        self._children = WeakNonHashableSet[Self]()
        self._modification_notification_callbacks = CallbackRegistry()

        for attr in vars(self).values():

            if isinstance(attr, ModificationNotifier):
                attr.onSettingModifiedCall(self._notifyModification)

    def derive(self: Self) -> Self:
        """
        Creates a new instance of this Section's class, and set this one as the
        parent of that instance.

        Returns:
            A new instance of this Section.
        """

        new = self.__class__()
        new.setParent(self)
        return new

    def setParent(self: Self, parent: Optional[Self]) -> None:
        """
        Makes the given Section the parent of this one. If None, remove this
        Section's parent, if any.

        All the Setting, List and Section fields defined on this Section
        instance will be recursively reparented to the corresponding Setting /
        List / Section field on the given parent.

        This method is for internal purposes and you will typically not need to
        call it directly.

        Args:
            parent: Either a Section that will become this Section's parent, or
                None. The parent Section must have the same type as this
                Section.

        Returns:
            None.

        Note:
            A Section and its parent, if any, do not increase each other's
            reference count.
        """

        # Runtime check to affirm the type check of the method.

        if parent is not None:
            if type(self) is not type(parent):
                return

        old_parent = self.parent()
        if old_parent is not None:
            old_parent._children.discard(self)

        if parent is None:
            self._parent = None
        else:
            self._parent = weakref.ref(parent)
            parent._children.add(self)

        for attrName, attr in vars(self).items():

            if not isinstance(attr, Inheriter):
                continue

            if parent is None:
                attr.setParent(None)  # type: ignore
                continue

            parentAttr = getattr(parent, attrName, None)
            if parentAttr is None:

                # This is a safety check, but it shouldn't happen. By
                # construction self should be of the same type as parent, so
                # they should have the same attributes.

                continue

            assert isinstance(parentAttr, Inheriter)
            assert type(attr) is type(parentAttr)  # type: ignore
            attr.setParent(parentAttr)  # type: ignore

    def parent(self: Self) -> Optional[Self]:
        """
        Returns the parent of this Section, if any.

        Returns:
            A Section instance of the same type as this one, or None.
        """

        return self._parent() if self._parent is not None else None

    def children(self: Self) -> Iterator[Self]:
        """
        Returns an iterator over the Section instances that have this Section
        as their parent.

        Returns:
            An iterator over Section instances of the same type as this one.
        """

        yield from self._children

    def onSettingModifiedCall(self, callback: Callable[[Self], None]) -> None:
        """
        Adds a callback to be called whenever any Setting defined on this
        Section or any of its own Section fields is modified in any way.

        The callback will be called with this Section instance as its argument.

        Args:
            callback: A callable that takes one argument of the same type as
                this Section, and that returns None.

        Returns:
            None.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._modification_notification_callbacks.add(callback)

    def dump(self) -> Sequence[tuple[str, str]]:
        """
        Internal.
        """

        ret: list[tuple[str, str]] = []

        for attrName, attr in sorted(vars(self).items()):
            if not isinstance(attr, Dumpable):
                continue

            if attrName.startswith("_"):
                continue

            for subAttrName, dump in attr.dump():
                name = ".".join(s for s in (attrName, subAttrName) if s)
                ret.append((name, dump))

        return ret

    def restore(self, data: Sequence[tuple[str, str]]) -> None:
        """
        Internal.
        """

        for name, dump in data:
            if "." in name:
                item_name, subname = name.split(".", 1)
            else:
                item_name, subname = name, ""

            try:
                item = getattr(self, item_name)
            except AttributeError:
                continue

            if not isinstance(item, Restorable):
                continue

            item.restore([(subname, dump)])

    def _notifyModification(self, value: ModificationNotifier) -> None:

        self._modification_notification_callbacks.callAll(self)


def NewSection(section: Type[SectionT]) -> SectionT:
    """
    Creates a new Section field of the given type, to be used in the definition
    of a Section or a Settings.

    This function must be used instead of normal instantiation when adding a
    Section to a Settings or another Section. (This is because, under the hood,
    both Section and Settings classes are dataclasses, and their attributes must
    be fields. This function takes care of that.)

    Args:
        section: The *type* of the Section to be created.

    Returns:
        A dataclass field bound to the given Section type.

    Note:
        It typically does not make sense to call this function outside of the
        definition of a Settings or a Section.

    Example:

    >>> import sunset
    >>> class ExampleSettings(sunset.Settings):
    ...     class ExampleSection(sunset.Section):
    ...         pass
    ...
    ...     subsection: ExampleSection = sunset.NewSection(ExampleSection)

    >>> settings = ExampleSettings()
    """

    return field(default_factory=section)
