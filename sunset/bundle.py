import dataclasses
import inspect
import weakref

from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    MutableSet,
    Optional,
    Type,
    TypeVar,
    cast,
)

from .non_hashable_set import WeakNonHashableSet
from .protocols import (
    Containable,
    ContainableImpl,
    Field,
    ItemTemplate,
    UpdateNotifier,
)
from .registry import CallbackRegistry


# TODO: Replace with typing.Self when mypy finally supports that.
Self = TypeVar("Self", bound="Bundle")


class Bundle(ContainableImpl):
    """
    A collection of related Keys.

    Under the hood, a Bundle is a dataclass, and can be used in the same manner,
    i.e. by defining attributes directly on the class itself.

    Example:

    >>> from sunset import Bundle, Key
    >>> class Appearance(Bundle):
    ...     class Font(Bundle):
    ...         name: Key[str] = Key(default="Arial")
    ...         size: Key[int] = Key(default=14)
    ...     main_font: Font      = Font()
    ...     secondary_font: Font = Font()
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

    _parent: Optional[weakref.ref["Bundle"]]
    _children: MutableSet["Bundle"]
    _fields: dict[str, Field]
    _update_notification_callbacks: CallbackRegistry[UpdateNotifier]
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
                            f" name declared in parent class"
                            f" '{cls_parent.__name__}'; consider"
                            f" renaming this field to '{name}_' for instance"
                        )

                setattr(
                    cls,
                    name,
                    dataclasses.field(default_factory=attr.newInstance),
                )

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

        wrapped = dataclasses.dataclass()(cls)
        return super().__new__(wrapped)

    def __post_init__(self) -> None:

        super().__init__()

        self._parent = None
        self._children = WeakNonHashableSet[Bundle]()
        self._fields = {}
        self._update_notification_callbacks = CallbackRegistry()
        self._update_notification_enabled = True

        for label, field in vars(self).items():

            if isinstance(field, Field):
                self._fields[label] = field
                field.setContainer(label, self)

    def fieldPath(self) -> str:
        """
        Internal.
        """

        return super().fieldPath() + self._PATH_SEPARATOR

    def containsFieldWithLabel(self, label: str, field: Containable) -> bool:
        """
        Internal.
        """

        return self._fields.get(label) is field

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

        for label, field in self._fields.items():

            if parent is None:
                field.setParent(None)
                continue

            parent_field = parent._fields.get(label)
            if parent_field is None:

                # This is a safety check, but it shouldn't happen. By
                # construction self should be of the same type as parent, so
                # they should have the same attributes.

                continue

            assert type(field) is type(parent_field)
            field.setParent(parent_field)

    def parent(self: Self) -> Optional[Self]:
        """
        Returns the parent of this Bundle, if any.

        Returns:
            A Bundle instance of the same type as this one, or None.
        """

        # Make the type of self._parent more specific for the purpose of type
        # checking.

        _parent = cast(Optional[weakref.ref[Self]], self._parent)
        return _parent() if _parent is not None else None

    def children(self: Self) -> Iterator[Self]:
        """
        Returns an iterator over the Bundle instances that have this Bundle
        as their parent.

        Returns:
            An iterator over Bundle instances of the same type as this one.
        """

        # Note that we iterate on a copy so that this will not break if a
        # different thread updates the contents during the iteration.

        for child in list(self._children):
            yield cast(Self, child)

    def onUpdateCall(self, callback: Callable[[Any], None]) -> None:
        """
        Adds a callback to be called whenever this Bundle is updated. A Bundle
        is considered updated when any of its fields is updated.

        The callback will be called with as its argument whichever field was
        just updated.

        Args:
            callback: A callable that will be called with one argument of type
                :class:`~sunset.List`, :class:`~sunset.Bundle` or
                :class:`~sunset.Key`, and returns None.

        Returns:
            None.

        Note:
            This method does not increase the reference count of the given
            callback.
        """

        self._update_notification_callbacks.add(callback)

    def isSet(self) -> bool:
        """
        Indicates whether this Bundle holds any field that is set.

        Returns:
            True if any field set on this Bundle is set, else False.
        """

        return any(field.isSet() for field in self._fields.values())

    def dumpFields(self) -> Iterable[tuple[str, Optional[str]]]:
        """
        Internal.
        """

        if not self.isPrivate():
            for _, field in sorted(self._fields.items()):
                yield from field.dumpFields()

    def restoreField(self, path: str, value: Optional[str]) -> None:
        """
        Internal.
        """

        if self._PATH_SEPARATOR not in path:
            return

        field_label, path = path.split(self._PATH_SEPARATOR, 1)
        if self.fieldLabel() != field_label:
            return

        field_label, *_ = path.split(self._PATH_SEPARATOR, 1)
        if (field := self._fields.get(field_label)) is not None:
            field.restoreField(path, value)

    def triggerUpdateNotification(
        self, field: Optional[UpdateNotifier]
    ) -> None:
        """
        Internal.
        """

        if not self._update_notification_enabled:
            return

        if field is None:
            field = self

        self._update_notification_callbacks.callAll(field)

        if (container := self.container()) is not None and not self.isPrivate():
            container.triggerUpdateNotification(field)

    def newInstance(self: Self) -> Self:
        """
        Internal. Returns a new instance of this Bundle with the same fields.

        Returns:
            A Bundle instance.
        """

        new = self.__class__()
        return new
