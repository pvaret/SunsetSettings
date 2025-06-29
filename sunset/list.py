import sys
import weakref
from collections.abc import Callable, Iterable, Iterator, MutableSequence
from enum import Enum, auto
from types import GenericAlias
from typing import Any, SupportsIndex, TypeVar, cast, overload

if sys.version_info < (3, 11):  # pragma: no cover
    from typing_extensions import Self
else:
    from typing import Self

from sunset.bunch import Bunch
from sunset.key import Key
from sunset.lock import SettingsLock
from sunset.notifier import Notifier
from sunset.protocols import BaseField, UpdateNotifier
from sunset.sets import WeakNonHashableSet
from sunset.stringutils import collate_by_prefix, split_on

ListItemT = TypeVar("ListItemT", bound=Bunch | Key[Any])


class IterOrder(Enum):
    NO_PARENT = auto()
    PARENT_FIRST = auto()
    PARENT_LAST = auto()


class List(MutableSequence[ListItemT], BaseField):
    """
    A list-like container for Keys or Bunches of a given type, to be used in a
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
        template: A Key or a Bunch *instance* that represents the items that
            will be contained in this List. (The template itself will not be
            added to the List.)

        order: One of `List.NO_PARENT`, `List.PARENT_FIRST` or
            `List.PARENT_LAST`. Sets the default iteration order used in
            :meth:`iter()` when not otherwise specified. Default:
            `List.NO_PARENT`.

    Example:

    >>> from sunset import Bunch, Key, List, Settings
    >>> class ExampleSettings(Settings):
    ...     class ExampleBunch(Bunch):
    ...         a: Key[str] = Key(default="")
    ...     key_list: List[Key[int]]         = List(Key(default=0))
    ...     bunch_list: List[ExampleBunch] = List(ExampleBunch())
    >>> settings = ExampleSettings()
    >>> settings.bunch_list
    []
    >>> settings.bunch_list.appendOne().a.set("demo")
    True
    >>> settings.bunch_list
    [ExampleSettings.ExampleBunch(a=<Key[str]:demo>)]
    >>> settings.key_list
    []
    >>> settings.key_list.appendOne().set(12)
    True
    >>> settings.key_list
    [<Key[int]:12>]
    """

    NO_PARENT = IterOrder.NO_PARENT
    PARENT_FIRST = IterOrder.PARENT_FIRST
    PARENT_LAST = IterOrder.PARENT_LAST

    _contents: list[ListItemT]
    _parent_ref: weakref.ref["List[ListItemT]"] | None
    _children_ref: WeakNonHashableSet["List[ListItemT]"]
    _iter_order: IterOrder
    _update_notifier: Notifier[[UpdateNotifier]]
    _template: ListItemT

    def __init__(
        self, template: ListItemT, order: IterOrder = IterOrder.NO_PARENT
    ) -> None:
        super().__init__()

        self._contents = []

        self._parent_ref = None
        self._children_ref = WeakNonHashableSet()
        self._iter_order = order
        self._update_notifier = Notifier()
        self._template = template

    @SettingsLock.with_write_lock
    def insert(self, index: SupportsIndex, value: ListItemT) -> None:
        self._contents.insert(index, value)
        self._relabelItems()
        self._update_notifier.trigger(self)

    @overload
    def __getitem__(self, index: SupportsIndex) -> ListItemT: ...

    @overload
    def __getitem__(self, index: slice) -> list[ListItemT]: ...

    @SettingsLock.with_read_lock
    def __getitem__(self, index: SupportsIndex | slice) -> ListItemT | list[ListItemT]:
        return self._contents[index]

    @overload
    def __setitem__(self, index: SupportsIndex, value: ListItemT) -> None: ...

    @overload
    def __setitem__(self, index: slice, value: Iterable[ListItemT]) -> None: ...

    @SettingsLock.with_write_lock
    def __setitem__(
        self, index: SupportsIndex | slice, value: ListItemT | Iterable[ListItemT]
    ) -> None:
        self._clearMetadata(self._contents[index])
        if isinstance(index, slice):
            assert isinstance(value, Iterable)  # noqa: S101
            self._contents[index] = value

        else:
            assert isinstance(index, SupportsIndex)  # noqa: S101
            assert not isinstance(value, Iterable)  # noqa: S101
            self._contents[index] = value

        self._relabelItems()
        self._update_notifier.trigger(self)

    @SettingsLock.with_write_lock
    def __delitem__(self, index: SupportsIndex | slice) -> None:
        self._clearMetadata(self._contents[index])
        del self._contents[index]
        self._relabelItems()
        self._update_notifier.trigger(self)

    @SettingsLock.with_write_lock
    def extend(self, values: Iterable[ListItemT]) -> None:
        self._contents.extend(values)
        self._relabelItems()
        self._update_notifier.trigger(self)

    @SettingsLock.with_write_lock
    def append(self, value: ListItemT) -> None:
        self.extend((value,))

    @SettingsLock.with_write_lock
    def __iadd__(self, values: Iterable[ListItemT]) -> Self:
        self.extend(values)
        return self

    @SettingsLock.with_write_lock
    def clear(self) -> None:
        del self[:]

    def _clearMetadata(self, fields: ListItemT | list[ListItemT]) -> None:
        for field in fields if isinstance(fields, list) else [fields]:
            field.meta().clear()
            field._update_notifier.discard(self._update_notifier.trigger)  # noqa: SLF001

    def __len__(self) -> int:
        return len(self._contents)

    def _newItem(self) -> ListItemT:
        return self._template._newInstance()  # noqa: SLF001

    @SettingsLock.with_read_lock
    def isSet(self) -> bool:
        """
        Indicates whether this List holds any item that is set.

        Returns:
            True if any item contained in this List is set, else False.
        """

        return any(item.isSet() for item in self._contents)

    @SettingsLock.with_write_lock
    def appendOne(self) -> ListItemT:
        """
        Creates a new item of the type contained in this List, appends it to
        this List, and returns it.

        Returns:
            An instance of the item type contained in this List.
        """

        item = self._newItem()
        self.append(item)
        return item

    @SettingsLock.with_write_lock
    def insertOne(self, index: int) -> ListItemT:
        """
        Creates a new item of the type contained in this List, inserts it in
        this List at the given index, and returns it.

        Args:
            index: The list index where to insert the new item.

        Returns:
            An instance of the item type contained in this List.
        """

        item = self._newItem()
        self.insert(index, item)
        return item

    def _relabelItems(self) -> None:
        for i, item in enumerate(self._contents):
            item.meta().update(label=self._labelForIndex(i), container=self)
            item._update_notifier.add(self._update_notifier.trigger)  # noqa: SLF001

    @staticmethod
    def _labelForIndex(index: SupportsIndex) -> str:
        return str(int(index) + 1)

    @staticmethod
    def _indexForLabel(label: str) -> int | None:
        if not label.isdigit():
            return None
        index = int(label) - 1
        return index if index >= 0 else None

    @SettingsLock.with_write_lock
    def setParent(self, parent: Self | None) -> None:
        """
        Makes the given List the parent of this one. If None, remove this List's
        parent, if any.

        Having a parent does not affect a List's behavior outside of the
        :meth:`iter()` method.

        This method is for internal purposes and you will typically not need to
        call it directly.

        Args:
            parent: Either a List that will become this List's parent, or
                None. The parent List must have the same type as this List.

        Note:
            A List and its parent, if any, do not increase each other's
            reference count.
        """

        # Runtime check to affirm the type check of the method.

        if parent is not None and type(self) is not type(parent):  # pragma: no cover
            return

        old_parent = self.parent()
        if old_parent is not None:
            old_parent._children_ref.discard(self)  # noqa: SLF001

        if parent is None:
            self._parent_ref = None
        else:
            self._parent_ref = weakref.ref(parent)
            parent._children_ref.add(self)  # noqa: SLF001

    @SettingsLock.with_read_lock
    def iter(self, order: IterOrder | None = None) -> Iterable[ListItemT]:
        """
        Returns the elements contained in this List, and optionally in its parents, if
        any.

        Args:
            order: One of `List.NO_PARENT`, `List.PARENT_FIRST`,
                `List.PARENT_LAST`, or None.

                - If `List.NO_PARENT`, this method only returns the contents of this
                  List instance.

                - If `List.PARENT_FIRST`, it recursively returns items from this List's
                  parents, if any, then from this List itself.

                - If `List.PARENT_LAST`, it returns items from this List itself, then
                  recursively from its parents, if any.

                - If None, the order set on the List itself at creation time
                  will be used.

                Default: None.

        Returns:
            An iterable on the items contained in this List and optionally its parents.

        Example:

        >>> from sunset import Key, List
        >>> show = lambda l: [key.get() for key in l]
        >>> parent = List(Key(default=0))
        >>> parent.appendOne().set(1)
        True
        >>> parent.appendOne().set(2)
        True
        >>> child = List(Key(default=0))
        >>> child.appendOne().set(3)
        True
        >>> child.appendOne().set(4)
        True
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

        ret: list[ListItemT] = []
        parent = self.parent()

        if order is None:
            order = self._iter_order

        if parent is not None and order == IterOrder.PARENT_FIRST:
            ret.extend(parent.iter(order))

        ret.extend(self._contents)

        if parent is not None and order == IterOrder.PARENT_LAST:
            ret.extend(parent.iter(order))

        return ret

    def __iter__(self) -> Iterator[ListItemT]:
        items = self.iter(IterOrder.NO_PARENT)
        yield from items

    @SettingsLock.with_read_lock
    def parent(self) -> Self | None:
        """
        Returns the parent of this List, if any.

        Returns:
            A List instance of the same type as this one, or None.
        """

        # Make the type of self._parent_ref more specific for the purpose of
        # type checking.

        parent = cast(weakref.ref[Self] | None, self._parent_ref)
        return parent() if parent is not None else None

    @SettingsLock.with_read_lock
    def children(self) -> Iterable[Self]:
        """
        Returns an iterable with the List instances that have this List as their parent.

        Returns:
            An iterable of List instances of the same type as this one.
        """

        return [cast(Self, child) for child in self._children_ref]

    def onUpdateCall(self, callback: Callable[[Any], Any]) -> None:
        """
        Adds a callback to be called whenever this List, *or* any item contained
        in this List, is updated.

        The callback will be called with whichever entity was updated as its
        argument: this List, or one of its items or sub-items.

        Adding new items to or deleting items from a List is considered an
        update of that List, not of the elements in question.

        Args:
            callback: A callable that will be called with one argument of type
                :class:`~sunset.List`, :class:`~sunset.Bunch` or
                :class:`~sunset.Key`.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._update_notifier.add(callback)

    @SettingsLock.with_read_lock
    def dumpFields(self) -> Iterable[tuple[str, str | None]]:
        """
        Internal.
        """

        ret: list[tuple[str, str | None]] = []
        sep = self._PATH_SEPARATOR
        if not self.skipOnSave():
            for i, item in enumerate(self._contents, start=1):
                label = str(i)
                if not item.isSet():
                    ret.append((label, None))
                else:
                    ret.extend(
                        (label + sep + path if path else label, child_item)
                        for path, child_item in item.dumpFields()
                    )

        return ret

    @SettingsLock.with_write_lock
    def restoreFields(self, fields: Iterable[tuple[str, str | None]]) -> bool:
        """
        Internal.
        """

        any_change = False

        by_label = collate_by_prefix(fields, split_on(self._PATH_SEPARATOR))
        by_index = {
            index: value
            for label, value in by_label.items()
            if (index := self._indexForLabel(label)) is not None
        }
        max_index = max(by_index.keys(), default=-1)

        with self._update_notifier.inhibit():
            if self._lastIndex > max_index:
                del self[max_index + 1 :]
                any_change = True
            else:
                any_change = self._ensureIndexExists(max_index)

            for i, field in enumerate(self):
                any_change = field.restoreFields(by_index.get(i, [])) or any_change

        return any_change

    @SettingsLock.with_write_lock
    def _ensureIndexExists(self, index: int) -> bool:
        missing_count = index - self._lastIndex

        if missing_count > 0:
            self.extend(self._newItem() for _ in range(missing_count))
            return True

        return False

    @property
    def _lastIndex(self) -> int:
        return len(self) - 1

    def _typeHint(self) -> GenericAlias:
        return GenericAlias(type(self), type(self._template))

    def _newInstance(self) -> Self:
        """
        Internal. Returns a new instance of this List capable of holding the
        same type.

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
