import inspect
import weakref

from dataclasses import dataclass, field
from typing import (
    Any,
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
from .protocols import (
    Dumpable,
    Inheriter,
    ItemTemplate,
    ModificationNotifier,
    Restorable,
)
from .registry import CallbackRegistry


SectionT = TypeVar("SectionT", bound="Section")


class Section:
    """
    A collection of related keys.

    Under the hood, a Section is a dataclass, and can be used in the same
    manner, i.e. by defining attributes directly on the class itself.

    Example:

    >>> from sunset import Key, Section
    >>> class MySection(Section):
    ...     class MySubsection(Section):
    ...         subkey = Key(default=0)
    ...     subsection1 = MySubsection()
    ...     subsection2 = MySubsection()
    >>> section = MySection()
    >>> section.subsection1.subkey.get()
    0
    >>> section.subsection2.subkey.get()
    0
    >>> section.subsection1.subkey.set(42)
    >>> section.subsection2.subkey.set(101)
    >>> section.subsection1.subkey.get()
    42
    >>> section.subsection2.subkey.get()
    101
    """

    _parent: Optional[weakref.ref[Self]]
    _children: MutableSet[Self]
    _modification_notification_callbacks: CallbackRegistry[Self]
    _modification_notification_enabled: bool

    def __new__(cls: Type[Self]) -> Self:

        # Automatically promote relevant attributes to dataclass fields.

        potential_fields = list(vars(cls).items())
        for name, attr in potential_fields:
            if isinstance(attr, ItemTemplate) and not inspect.isclass(attr):
                setattr(cls, name, field(default_factory=attr.new))

                # Dataclass instantiation raises an error if a field does not
                # have an explicit type annotation. But our Key, List and
                # Section fields are unambiguously typed, so we don't actually
                # need the annotation. So we just tell the dataclass that the
                # type of non-explicitly-annotated fields is 'Any'. Turns out,
                # this works.

                # Also note the subtle dance here: the annotations need to be on
                # *this* class, and not inherited from a parent class. So we
                # make sure that the __annotations__ mapping does exist in this
                # class' namespace.

                if "__annotations__" not in cls.__dict__:
                    setattr(cls, "__annotations__", {})
                cls.__annotations__.setdefault(name, Any)

        # Create a new instance of this class wrapped as a dataclass.

        wrapped = dataclass()(cls)
        return super().__new__(wrapped)

    def __post_init__(self: Self) -> None:

        self._parent = None
        self._children = WeakNonHashableSet[Self]()
        self._modification_notification_callbacks = CallbackRegistry()
        self._modification_notification_enabled = True

        for attr in vars(self).values():

            if isinstance(attr, ModificationNotifier):
                attr.onKeyModifiedCall(self._notifyModification)

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

        All the Key, List and Section fields defined on this Section instance
        will be recursively reparented to the corresponding Key / List / Section
        field on the given parent.

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

    def onKeyModifiedCall(self, callback: Callable[[Self], None]) -> None:
        """
        Adds a callback to be called whenever any Key defined on this Section or
        any of its own Section fields is modified in any way.

        The callback will be called with this Section as its argument.

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

        notification_enabled = self._modification_notification_enabled
        self._modification_notification_enabled = False

        subitems: dict[str, list[tuple[str, str]]] = {}

        for name, dump in data:
            if "." in name:
                item_name, subname = name.split(".", 1)
            else:
                item_name, subname = name, ""

            subitems.setdefault(item_name, []).append((subname, dump))

        for item_name in subitems:

            try:
                item = getattr(self, item_name)
            except AttributeError:
                continue

            if not isinstance(item, Restorable):
                continue

            item.restore(subitems[item_name])

        self._modification_notification_enabled = notification_enabled
        self._notifyModification(self)

    def _notifyModification(self, value: ModificationNotifier) -> None:

        if self._modification_notification_enabled:
            self._modification_notification_callbacks.callAll(self)

    def new(self) -> Self:
        """
        Returns a new instance of this Section with the same fields.

        Returns:
            A Section instance.
        """

        return self.__class__()
