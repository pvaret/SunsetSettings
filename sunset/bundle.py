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
    UpdateNotifier,
    Restorable,
)
from .registry import CallbackRegistry


BundleT = TypeVar("BundleT", bound="Bundle")


class Bundle:
    """
    A collection of related Keys.

    Under the hood, a Bundle is a dataclass, and can be used in the same manner,
    i.e. by defining attributes directly on the class itself.

    Example:

    >>> from sunset import Bundle, Key
    >>> class Appearance(Bundle):
    ...     class Font(Bundle):
    ...         name = Key(default="Arial")
    ...         size = Key(default=14)
    ...     main_font = Font()
    ...     secondary_font = Font()
    >>> appearance = Appearance()
    >>> appearance.main_font.name.get()
    'Arial'
    >>> appearance.secondary_font.name.get()
    'Arial'
    >>> appearance.main_font.name.set("Times New Roman")
    >>> appearance.secondary_font.name.set("Calibri")
    >>> appearance.main_font.name.get()
    'Times New Roman'
    >>> appearance.secondary_font.name.get()
    'Calibri'
    """

    _parent: Optional[weakref.ref[Self]]
    _children: MutableSet[Self]
    _update_notification_callbacks: CallbackRegistry[Self]
    _update_notification_enabled: bool

    def __new__(cls: Type[Self]) -> Self:

        # Automatically promote relevant attributes to dataclass fields.

        cls_parents = cls.__bases__

        potential_fields = list(vars(cls).items())
        for name, attr in potential_fields:

            if inspect.isclass(attr):

                if attr.__name__ == name:

                    # This is probably a class definition that just happens to
                    # be located inside the containing Bundle definition. This
                    # is fine.

                    continue

                raise TypeError(
                    f"Field '{name}' in the definition of '{cls.__name__}'"
                    " is uninstantiated"
                )

            if isinstance(attr, ItemTemplate):

                # Safety check: make sure the user isn't accidentally overriding
                # an existing attribute.

                for cls_parent in cls_parents:
                    if getattr(cls_parent, name, None) is not None:
                        raise TypeError(
                            f"Field '{name}' in the definition of"
                            f" '{cls.__name__}' overrides attribute of the same"
                            f" name declared in parent class "
                            f"'{cls_parent.__name__}'; consider"
                            f" renaming this field to '{name}_' for instance"
                        )

                setattr(cls, name, field(default_factory=attr.new))

                # Dataclass instantiation raises an error if a field does not
                # have an explicit type annotation. But our Key, List and
                # Bundle fields are unambiguously typed, so we don't actually
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
        self._update_notification_callbacks = CallbackRegistry()
        self._update_notification_enabled = True

        for attr in vars(self).values():

            if isinstance(attr, UpdateNotifier):
                attr.onUpdateCall(self._notifyUpdate)

    def setParent(self: Self, parent: Optional[Self]) -> None:
        """
        Makes the given Bundle the parent of this one. If None, remove this
        Bundle's parent, if any.

        All the Key, List and Bundle fields defined on this Bundle instance
        will be recursively reparented to the corresponding Key / List / Bundle
        field on the given parent.

        This method is for internal purposes and you will typically not need to
        call it directly.

        Args:
            parent: Either a Bundle that will become this Bundle's parent, or
                None. The parent Bundle must have the same type as this
                Bundle.

        Returns:
            None.

        Note:
            A Bundle and its parent, if any, do not increase each other's
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
        Returns the parent of this Bundle, if any.

        Returns:
            A Bundle instance of the same type as this one, or None.
        """

        return self._parent() if self._parent is not None else None

    def children(self: Self) -> Iterator[Self]:
        """
        Returns an iterator over the Bundle instances that have this Bundle
        as their parent.

        Returns:
            An iterator over Bundle instances of the same type as this one.
        """

        yield from self._children

    def onUpdateCall(self, callback: Callable[[Self], None]) -> None:
        """
        Adds a callback to be called whenever this Bundle or any of its fields
        is updated.

        The callback will be called with this Bundle as its argument.

        Args:
            callback: A callable that takes one argument of the same type as
                this Bundle, and that returns None.

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

        notification_enabled = self._update_notification_enabled
        self._update_notification_enabled = False

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

        self._update_notification_enabled = notification_enabled
        self._notifyUpdate(self)

    def _notifyUpdate(self, value: UpdateNotifier) -> None:

        if self._update_notification_enabled:
            self._update_notification_callbacks.callAll(self)

    def new(self: Self) -> Self:
        """
        Returns a new instance of this Bundle with the same fields.

        Returns:
            A Bundle instance.
        """

        return self.__class__()
