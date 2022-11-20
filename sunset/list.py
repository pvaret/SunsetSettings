import weakref

from enum import Enum, auto
from itertools import tee
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    MutableSequence,
    Optional,
    Sequence,
    SupportsIndex,
    TypeVar,
    Union,
    overload,
)

from typing_extensions import Self

from .bundle import Bundle
from .key import Key
from .non_hashable_set import WeakNonHashableSet
from .registry import CallbackRegistry

ListItemT = TypeVar(
    "ListItemT",
    # Note that we match on Key[Any] and not Key[SerializableT], because a
    # TypeVar cannot be defined in terms of another TypeVar. This is fine,
    # because Keys can only be created bound to a SerializableT type anyway.
    bound=Union[Bundle, Key[Any]],
)


class IterOrder(Enum):
    NO_PARENT = auto()
    PARENT_FIRST = auto()
    PARENT_LAST = auto()


class List(MutableSequence[ListItemT]):
    """
    A list-like container for Keys or Bundles of a given type, to be used in a
    Settings' definition.

    It is type-compatible with standard Python lists and supports indexing,
    insertion, appending, etc.

    In addition, it offers support for update notification callbacks, and
    inheritance. The inheritance is used when iterating on the List's contents
    using the :meth:`iter()` method, which iterates on a List and, optionally,
    its parents.

    Instead of creating a new instance of the contained type and inserting or
    appending it, you can use the :meth:`appendOne()` or :meth:`insertOne()`
    methods to do it in one step.

    Args:
        template: A Key or a Bundle *instance* that represents the items that
            will be contained in this List. (The template itself will not be
            added to the List.)
        order: One of List.NO_PARENT, List.PARENT_FIRST or List.PARENT_LAST.
            Sets the default iteration order used in :meth:`iter()` when not
            otherwise specified. Default: List.NO_PARENT.

    Example:

    >>> from sunset import Bundle, Key, List, Settings
    >>> class ExampleSettings(Settings):
    ...     class ExampleBundle(Bundle):
    ...         a = Key(default="")
    ...     key_list = List(Key(default=0))
    ...     bundle_list = List(ExampleBundle())
    >>> settings = ExampleSettings()
    >>> settings.bundle_list
    []
    >>> settings.bundle_list.appendOne().a.set("demo")
    >>> settings.bundle_list
    [ExampleSettings.ExampleBundle(a=<Key[str]:demo>)]
    >>> settings.key_list
    []
    >>> settings.key_list.appendOne().set(12)
    >>> settings.key_list
    [<Key[int]:12>]
    """

    NO_PARENT = IterOrder.NO_PARENT
    PARENT_FIRST = IterOrder.PARENT_FIRST
    PARENT_LAST = IterOrder.PARENT_LAST

    _contents: list[ListItemT]
    _parent: Optional[weakref.ref[Self]]
    _children: WeakNonHashableSet[Self]
    _iter_order: IterOrder
    _update_notification_callbacks: CallbackRegistry[Self]
    _update_notification_enabled: bool
    _template: ListItemT

    def __init__(
        self, template: ListItemT, order: IterOrder = IterOrder.NO_PARENT
    ) -> None:

        super().__init__()

        self._contents = []

        self._parent = None
        self._children = WeakNonHashableSet()
        self._iter_order = order
        self._update_notification_callbacks = CallbackRegistry()
        self._update_notification_enabled = True
        self._template = template

    def insert(self, index: SupportsIndex, value: ListItemT) -> None:

        self._contents.insert(index, value)
        self._notifyUpdate(self)

        value.onUpdateCall(self._notifyUpdate)

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
                item.onUpdateCall(self._notifyUpdate)

        else:
            assert isinstance(index, SupportsIndex)

            self._contents[index] = value
            value.onUpdateCall(self._notifyUpdate)

        self._notifyUpdate(self)

    def __delitem__(self, index: Union[SupportsIndex, slice]) -> None:

        del self._contents[index]
        self._notifyUpdate(self)

    def extend(self, values: Iterable[ListItemT]) -> None:

        self._contents.extend(values)
        for value in values:
            value.onUpdateCall(self._notifyUpdate)
        self._notifyUpdate(self)

    def __iadd__(self, values: Iterable[ListItemT]) -> Self:

        self.extend(values)
        return self

    def clear(self) -> None:

        self._contents.clear()
        self._notifyUpdate(self)

    def __len__(self) -> int:

        return len(self._contents)

    def appendOne(self) -> ListItemT:
        """
        Creates a new item of the type contained in this List, appends it to
        this List, and returns it.

        Returns:
            An instance of the item type contained in this List.
        """

        item = self._template.new()
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

        item = self._template.new()
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

    def iter(self, order: Optional[IterOrder] = None) -> Iterator[ListItemT]:
        """
        Yields the elements contained in this List, and optionally in its
        parents, if any.

        Args:
            order: One of List.NO_PARENT, List.PARENT_FIRST, List.PARENT_LAST,
                or None. If None, the order set on the List itself at creation
                time will be used. If List.NO_PARENT, this method only yields
                the contents of this List instance. If List.PARENT_FIRST, it
                yields from this List's parents, if any, then this List itself.
                If List.PARENT_LAST, it yields from this List itself, then from
                its parents if any. Default: None.

        Returns:
            An iterator over the items contained in this List and optionally its
                parents.

        Example:

        >>> from sunset import Key, List
        >>> show = lambda l: [key.get() for key in l]
        >>> parent = List(Key(default=0))
        >>> parent.appendOne().set(1)
        >>> parent.appendOne().set(2)
        >>> child = List(Key(default=0))
        >>> child.appendOne().set(3)
        >>> child.appendOne().set(4)
        >>> show(parent)
        [1, 2]
        >>> show(child)
        [3, 4]
        >>> child.setParent(parent)
        >>> show(child.iter())
        [3, 4]
        >>> show(child.iter(order=List.PARENT_FIRST))
        [1, 2, 3, 4]
        >>> show(child.iter(order=List.PARENT_LAST))
        [3, 4, 1, 2]
        """

        parent = self.parent()

        if order is None:
            order = self._iter_order

        if parent is not None and order == IterOrder.PARENT_FIRST:
            yield from parent.iter(order)

        yield from self._contents

        if parent is not None and order == IterOrder.PARENT_LAST:
            yield from parent.iter(order)

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

    def onUpdateCall(self, callback: Callable[[Self], None]) -> None:
        """
        Adds a callback to be called whenever this List, *or* any item contained
        in this List, is updated.

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

        self._update_notification_callbacks.add(callback)

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

        notification_enabled = self._update_notification_enabled
        self._update_notification_enabled = False

        subitems: dict[str, list[tuple[str, str]]] = {}

        for name, dump in data:
            if "." in name:
                item_name, subname = name.split(".", 1)
            else:
                item_name, subname = name, ""

            if not item_name.isdigit():
                continue

            subitems.setdefault(item_name, []).append((subname, dump))

        for k in sorted(subitems.keys(), key=int):
            item = self._template.new()
            item.restore(subitems[k])
            self.append(item)

        self._update_notification_enabled = notification_enabled
        self._notifyUpdate(self)

    def _notifyUpdate(self, value: Union[ListItemT, Self]) -> None:

        if self._update_notification_enabled:

            # Note that if the sender is a List item, we only propagate the
            # notification if that item is still in this List.

            if isinstance(value, List) or value in self:
                self._update_notification_callbacks.callAll(self)

    def new(self) -> Self:
        """
        Returns a new instance of this List capable of holding the same type.

        Returns:
            A new List.
        """

        return self.__class__(template=self._template, order=self._iter_order)

    def __repr__(self) -> str:

        parent = self.parent()
        items = [repr(item) for item in self.iter(order=IterOrder.NO_PARENT)]
        if parent is not None and self._iter_order == IterOrder.PARENT_FIRST:
            items.insert(0, "<parent>")
        if parent is not None and self._iter_order == IterOrder.PARENT_LAST:
            items.append("<parent>")

        ret = "["
        ret += ",".join(items)
        ret += "]"
        return ret
