import weakref

from dataclasses import field
from typing import (
    Any,
    Callable,
    Iterator,
    MutableSequence,
    Optional,
    Sequence,
    SupportsIndex,
    Type,
    Union,
)

from typing_extensions import Self

from .non_hashable_set import WeakNonHashableSet
from .registry import CallbackRegistry
from .section import SectionT


class List(MutableSequence[SectionT]):
    """
    A list of Section instances of the same type.

    It is type-compatible with standard Python lists and supports indexing,
    insertion, appending, etc.

    In addition, it offers support for change notification callbacks, and
    inheritance. The inheritance is used in the `iterAll()` method, which
    iterates on a List and its parent.

    When adding a List to a Settings or a Section definition, do not instantiate
    the List class directly; use the `sunset.NewList()` function instead.

    Example:

    >>> import sunset
    >>> class ExampleSettings(sunset.Settings):
    ...     class ExampleSection(sunset.Section):
    ...         pass
    ...
    ...     list: sunset.List[ExampleSection] = sunset.NewList(ExampleSection)

    >>> settings = ExampleSettings()
    >>> settings.list.append(ExampleSettings.ExampleSection())
    """

    _contents: list[SectionT]
    _parent: Optional[weakref.ref[Self]]
    _children: WeakNonHashableSet[Self]
    _modification_notification_callbacks: CallbackRegistry[Self]
    _type: Type[SectionT]

    def __init__(self, _type: Type[SectionT]) -> None:

        self._contents = []

        self._parent = None
        self._children = WeakNonHashableSet()
        self._modification_notification_callbacks = CallbackRegistry()

        self._type = _type

    def insert(self, index: SupportsIndex, value: SectionT) -> None:

        self._contents.insert(index, value)
        self._notifyModification(self)

        value.onSettingModifiedCall(self._notifyModification)

    def __getitem__(self, index: SupportsIndex) -> SectionT:

        return self._contents[index]

    def __setitem__(self, index: SupportsIndex, value: SectionT) -> None:

        self._contents[index] = value
        self._notifyModification(self)

        value.onSettingModifiedCall(self._notifyModification)

    def __delitem__(self, index: SupportsIndex) -> None:

        del self._contents[index]
        self._notifyModification(self)

    def __len__(self) -> int:

        return len(self._contents)

    def setParent(self, parent: Optional[Self]):
        """
        Makes the given List the parent of this one. If None, remove this List's
        parent, if any.

        Having a parent does not affect a List's behavior outside of the
        `iterAll()` method.

        This method is for internal purposes and you will typically not need to
        call it directly.

        Args:
            parent: Either a List that will become this List's parent, or
                None. The parent List must have the same type as this List.

        Returns:
            None.

        Note:
            A List and its parent, if any, do not increase each other's
            reference count.
        """

        old_parent = self.parent()
        if old_parent is not None:
            old_parent._children.discard(self)

        if parent is None:
            self._parent = None
        else:
            self._parent = weakref.ref(parent)
            parent._children.add(self)

    def iterAll(self) -> Iterator[SectionT]:
        """
        Yields the element contained in this List and its parent, if any.

        Returns:
            An iterator over Section instances.

        Example:

        >>> import sunset
        >>> class ExampleSection(sunset.Section):
        ...     item: sunset.Setting[int] = sunset.NewSetting(default=0)

        >>> show = lambda l: [elt.item.get() for elt in l]

        >>> l1 = sunset.List(ExampleSection)
        >>> l1.append(ExampleSection())
        >>> l1.append(ExampleSection())
        >>> l1[0].item.set(1)
        >>> l1[1].item.set(2)

        >>> l2 = sunset.List(ExampleSection)
        >>> l2.append(ExampleSection())
        >>> l2.append(ExampleSection())
        >>> l2[0].item.set(3)
        >>> l2[1].item.set(4)

        >>> show(l1)
        [1, 2]
        >>> show(l2)
        [3, 4]

        >>> show(l1.iterAll())
        [1, 2]
        >>> l1.setParent(l2)
        >>> show(l1.iterAll())
        [1, 2, 3, 4]
        """

        yield from self
        parent = self.parent()
        if parent is not None:
            yield from parent.iterAll()

    def parent(self) -> Optional[Self]:
        """
        Returns the parent of this List, if any.

        Returns:
            A List instance of the same type as this one, or None.
        """

        return self._parent() if self._parent is not None else None

    def children(self) -> Iterator[Self]:
        """
        Returns an iterator over the List instances that have this List
        as their parent.

        Returns:
            An iterator over List instances of the same type as this one.
        """

        yield from self._children

    def onSettingModifiedCall(self, callback: Callable[[Self], None]) -> None:
        """
        Adds a callback to be called whenever this List, or any Setting defined
        on a Section contained in this List, is modified in any way.

        The callback will be called with this List instance as its argument.

        Args:
            callback: A callable that takes one argument of the same type as
                this List, and that returns None.

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

        # Count from 1, as it's more human friendly.

        for i, value in enumerate(self, start=1):
            for subAttrName, dump in value.dump():
                name = ".".join(s for s in (str(i), subAttrName) if s)
                ret.append((name, dump))

        return ret

    def restore(self, data: Sequence[tuple[str, str]]) -> None:
        """
        Internal.
        """

        subitems: dict[str, SectionT] = {}

        for name, dump in data:
            if "." in name:
                item_name, subname = name.split(".", 1)
            else:
                item_name, subname = name, ""
            if item_name not in subitems:
                subitems[item_name] = self._type()
                self.append(subitems[item_name])

            subitems[item_name].restore([(subname, dump)])

    def _notifyModification(self, value: Union[SectionT, Self]) -> None:

        if isinstance(value, List) or value in self:
            self._modification_notification_callbacks.callAll(self)


def NewList(section: Type[SectionT]) -> List[SectionT]:
    """
    Creates a new List field for the given Section type, to be used in the
    definition of a Section or a Settings.

    This function must be used instead of normal instantiation when adding a
    List to a Settings or a Section definition. (This is because, under the
    hood, both Section and Settings classes are dataclasses, and their
    attributes must be dataclass fields. This function takes care of that.)

    Args:
        section: The *type* of the Section instances that will be held in this
            List.

    Returns:
        A dataclass field bound to a List of the requisite type.

    Note:
        It typically does not make sense to call this function outside of the
        definition of a Settings or a Section.

    Example:

    >>> import sunset
    >>> class ExampleSettings(sunset.Settings):
    ...     class ExampleSection(sunset.Section):
    ...         pass
    ...
    ...     list: sunset.List[ExampleSection] = sunset.NewList(ExampleSection)

    >>> settings = ExampleSettings()
    >>> settings.list.append(ExampleSettings.ExampleSection())
    """

    factory: Callable[[], List[Any]] = lambda: List[SectionT](section)
    return field(default_factory=factory)
