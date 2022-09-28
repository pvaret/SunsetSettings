import weakref

from itertools import tee
from dataclasses import field
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    MutableSequence,
    Optional,
    Sequence,
    SupportsIndex,
    Type,
    TypeVar,
    Union,
    overload,
)

from typing_extensions import Self

from .non_hashable_set import WeakNonHashableSet
from .registry import CallbackRegistry
from .section import Section, SectionT
from .serializers import SerializableT
from .setting import Setting

ListItemT = TypeVar(
    "ListItemT",
    # Note that we match on Setting[Any] and not Setting[SerializableT],
    # because a TypeVar cannot be defined in terms of another TypeVar. This is
    # fine, because Setting instances can only be created bound to a
    # SerializableT type anyway.
    bound=Union[Section, Setting[Any]],
)


class List(MutableSequence[ListItemT]):
    """
    A container for lists of Setting or Section instances of the same type, to
    be used in a Settings' definition.

    It is type-compatible with standard Python lists and supports indexing,
    insertion, appending, etc.

    In addition, it offers support for update notification callbacks, and
    inheritance. The inheritance is used in the :meth:`iterAll()` method, which
    iterates on a List and its parent.

    When adding a List to a Settings or a Section definition, do not
    instantiate the List class directly; use the
    :func:`sunset.NewSectionList()` and :func:`sunset.NewSettingList()`
    functions instead.

    Instead of creating a new instance of the contained type and inserting or
    appending it, you can use the :meth:`appendOne()` or :meth:`insertOne()`
    methods to do it in one step.

    Args:
        factory: A callable that takes no argument and returns a new item
            of the type contained in this List.

    Example:

    >>> import sunset
    >>> class ExampleSettings(sunset.Settings):
    ...     class ExampleSection(sunset.Section):
    ...         a: sunset.Setting[str] = sunset.NewSetting(default="")
    ...
    ...     setting_list: sunset.List[sunset.Setting[int]] = (
    ...         sunset.NewSettingList(default=0))
    ...     section_list: sunset.List[ExampleSection] = sunset.NewSectionList(
    ...         ExampleSection)

    >>> settings = ExampleSettings()
    >>> settings.section_list.appendOne().a.set("demo")
    >>> settings.section_list
    [ExampleSettings.ExampleSection(a=<Setting[str]:demo>)]
    >>> settings.setting_list.appendOne().set(12)
    >>> settings.setting_list
    [<Setting[int]:12>]
    """

    _contents: list[ListItemT]
    _parent: Optional[weakref.ref[Self]]
    _children: WeakNonHashableSet[Self]
    _modification_notification_callbacks: CallbackRegistry[Self]
    _modification_notification_enabled: bool
    _item_factory: Callable[[], ListItemT]

    def __init__(self, factory: Callable[[], ListItemT]) -> None:

        self._contents = []

        self._parent = None
        self._children = WeakNonHashableSet()
        self._modification_notification_callbacks = CallbackRegistry()
        self._modification_notification_enabled = True

        self._item_factory = factory

    def insert(self, index: SupportsIndex, value: ListItemT) -> None:

        self._contents.insert(index, value)
        self._notifyModification(self)

        value.onSettingModifiedCall(self._notifyModification)

    @overload
    def __getitem__(self, index: SupportsIndex) -> ListItemT:
        ...

    @overload
    def __getitem__(self, index: slice) -> list[ListItemT]:
        ...

    def __getitem__(
        self, index: Union[SupportsIndex, slice]
    ) -> Union[ListItemT, list[ListItemT]]:

        return self._contents[index]

    @overload
    def __setitem__(self, index: SupportsIndex, value: ListItemT) -> None:
        ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[ListItemT]) -> None:
        ...

    def __setitem__(
        self,
        index: Union[SupportsIndex, slice],
        value: Union[ListItemT, Iterable[ListItemT]],
    ) -> None:

        if isinstance(value, Iterable):
            assert isinstance(index, slice)

            # Take a copy of the iterable, because it's not a given that it will
            # be iterable twice.

            value, value_copy = tee(value)

            self._contents[index] = value

            for item in value_copy:
                item.onSettingModifiedCall(self._notifyModification)

        else:
            assert isinstance(index, SupportsIndex)

            self._contents[index] = value
            value.onSettingModifiedCall(self._notifyModification)

        self._notifyModification(self)

    def __delitem__(self, index: Union[SupportsIndex, slice]) -> None:

        del self._contents[index]
        self._notifyModification(self)

    def extend(self, values: Iterable[ListItemT]) -> None:

        self._contents.extend(values)
        for value in values:
            value.onSettingModifiedCall(self._notifyModification)
        self._notifyModification(self)

    def __iadd__(self, values: Iterable[ListItemT]) -> Self:

        self.extend(values)
        return self

    def clear(self) -> None:

        self._contents.clear()
        self._notifyModification(self)

    def __len__(self) -> int:

        return len(self._contents)

    def appendOne(self) -> ListItemT:
        """
        Creates a new item of the type contained in this List, appends it to
        this List, and returns it.

        Returns:
            An instance of the item type contained in this List.
        """

        item = self._item_factory()
        self.append(item)
        return item

    def insertOne(self, index: int) -> ListItemT:
        """
        Creates a new item of the type contained in this List, inserts it in
        this List at the given index, and returns it.

        Args:
            index: The list index where to insert the new item.

        Returns:
            An instance of the item type contained in this List.
        """

        item = self._item_factory()
        self.insert(index, item)
        return item

    def setParent(self, parent: Optional[Self]):
        """
        Makes the given List the parent of this one. If None, remove this List's
        parent, if any.

        Having a parent does not affect a List's behavior outside of the
        :meth:`iterAll()` method.

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

    def iterAll(self) -> Iterator[ListItemT]:
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
        >>> l1.appendOne().item.set(1)
        >>> l1.appendOne().item.set(2)
        >>> l2 = sunset.List(ExampleSection)
        >>> l2.appendOne().item.set(3)
        >>> l2.appendOne().item.set(4)


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

        subitems: dict[str, ListItemT] = {}

        notification_enabled = self._modification_notification_enabled
        self._modification_notification_enabled = False

        for name, dump in data:
            if "." in name:
                item_name, subname = name.split(".", 1)
            else:
                item_name, subname = name, ""
            if item_name not in subitems:
                factory = self._item_factory
                subitems[item_name] = factory()
                self.append(subitems[item_name])

            subitems[item_name].restore([(subname, dump)])

        self._modification_notification_enabled = notification_enabled
        self._notifyModification(self)

    def _notifyModification(self, value: Union[ListItemT, Self]) -> None:

        if self._modification_notification_enabled:

            # Note that if the sender is a Section, we only propagate the
            # notification if that Section is still in this List.

            if isinstance(value, List) or value in self:
                self._modification_notification_callbacks.callAll(self)

    def __repr__(self) -> str:

        ret = "["
        ret += ",".join(repr(item) for item in self)
        ret += "]"
        return ret


def NewSectionList(section: Type[SectionT]) -> List[SectionT]:
    """
    Creates a new List field that will contain instances of the given Section
    type. This field can be used in the definition of a Section or a Settings.

    This function must be used instead of normal instantiation when adding a
    List of Section instances to a Settings or a Section definition. (This is
    because, under the hood, both Section and Settings classes are dataclasses,
    and their attributes must be dataclass fields. This function takes care of
    that.)

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
    ...     list: sunset.List[ExampleSection] = sunset.NewSectionList(
    ...         ExampleSection)

    >>> settings = ExampleSettings()
    >>> settings.list.appendOne()
    ExampleSettings.ExampleSection()
    """

    factory: Callable[[], List[SectionT]] = lambda: List[SectionT](section)
    return field(default_factory=factory)


def NewSettingList(
    default: SerializableT,
) -> List[Setting[SerializableT]]:
    """
    Creates a new List field for the given Setting type, to be used in the
    definition of a Section or a Settings.

    This function must be used instead of normal instantiation when adding a
    List of Setting instances to a Settings or a Section definition. (This is
    because, under the hood, both Section and Settings classes are dataclasses,
    and their attributes must be dataclass fields. This function takes care of
    that.)

    Args:
        default: The default value for the Setting instances that will be held
            in this List.

    Returns:
        A dataclass field bound to a List of the requisite type.

    Note:
        It typically does not make sense to call this function outside of the
        definition of a Settings or a Section.

    Example:

    >>> import sunset
    >>> class ExampleSettings(sunset.Settings):
    ...     list: sunset.List[sunset.Setting[int]] = sunset.NewSettingList(
    ...         default=0)

    >>> settings = ExampleSettings()
    >>> settings.list.appendOne()
    <Setting[int]:0>
    """

    def setting_factory() -> Setting[SerializableT]:
        return Setting(default=default)

    factory: Callable[[], List[Setting[SerializableT]]] = lambda: List[
        Setting[SerializableT]
    ](setting_factory)
    return field(default_factory=factory)
