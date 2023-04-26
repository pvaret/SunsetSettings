import dataclasses
import inspect
import weakref

from typing import (
    Any,
    Callable,
    Iterator,
    MutableSet,
    Optional,
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
Self = TypeVar("Self", bound="Bunch")


class Bunch(ContainableImpl):
    """
    A collection of related Keys.

    Under the hood, a Bunch is a dataclass, and can be used in the same manner,
    i.e. by defining attributes directly on the class itself.

    Example:

    >>> from sunset import Bunch, Key
    >>> class Appearance(Bunch):
    ...     class Font(Bunch):
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
    True
    >>> appearance.secondary_font.name.set("Calibri")
    True
    >>> appearance.main_font.name.get()
    'Times New Roman'
    >>> appearance.secondary_font.name.get()
    'Calibri'
    """

    _parent: Optional[weakref.ref["Bunch"]]
    _children: MutableSet["Bunch"]
    _fields: dict[str, Field]
    _update_notification_callbacks: CallbackRegistry[UpdateNotifier]
    _update_notification_enabled: bool
    _stored_defaults: dict[str, Any] = {}

    def __new__(cls: type[Self], **defaults: Any) -> Self:
        # Build and return a dataclass constructed from this class. Keep a
        # reference to that dataclass as a private class attribute, so that we
        # only construct it once. This allows type identity checks (as in
        # "type(a) is type (b)") to work.

        del defaults  # unused in __new___().

        _dataclass_attr = "__DATACLASS_CLASS"

        dataclass_class: Optional[type[Self]] = None
        if (dataclass_class := getattr(cls, _dataclass_attr, None)) is None:
            # We haven't yet constructed a dataclass from this class. Construct
            # one here.

            cls_parents = cls.__bases__

            dataclasses_fields: list[Any] = []

            potential_fields = list(vars(cls).items())
            for name, attr in potential_fields:
                if inspect.isclass(attr):
                    if attr.__name__ == name:
                        # This is probably a class definition that just happens
                        # to be located inside the containing Bunch definition.
                        # This is fine.

                        continue

                    raise TypeError(
                        f"Field '{name}' in the definition of '{cls.__name__}'"
                        " is uninstantiated"
                    )

                if isinstance(attr, ItemTemplate):
                    # Safety check: make sure the user isn't accidentally
                    # overriding an existing attribute.

                    for cls_parent in cls_parents:
                        if getattr(cls_parent, name, None) is not None:
                            raise TypeError(
                                f"Field '{name}' in the definition of"
                                f" '{cls.__name__}' overrides attribute of the"
                                " same name declared in parent class"
                                f" '{cls_parent.__name__}'; consider renaming"
                                f" this field to '{name}_' for instance"
                            )

                    # Create a proper field from the attribute.

                    field = dataclasses.field(default_factory=attr.newInstance)
                    dataclasses_fields.append((name, attr.typeHint(), field))

                    # Note that we delete the attribute now that the field is
                    # created. This helps avoid a hard-to-debug problem if the
                    # user subclasses a Bunch with a custom __init__() that
                    # doesn't call super().__init__(). That would seem to work,
                    # but any updates made to attributes of that bunch would
                    # really be applied to the attribute of the Bunch *class*,
                    # not the instance, which would cause 'weird action at a
                    # distance' bugs. Deleting the original class attribute
                    # prevents this entirely.

                    delattr(cls, name)

            # Create a dataclass based on this class. Note that we will be
            # providing our own __init__() override below.

            dataclass_class = cast(
                type[Self],
                dataclasses.make_dataclass(
                    cls.__qualname__,
                    dataclasses_fields,
                    init=False,
                    bases=(cls,) + cls_parents,
                ),
            )

            # And store it on the class itself for later.

            setattr(cls, _dataclass_attr, dataclass_class)

        # And finally, return an instance of the dataclass. Phew.

        return super().__new__(dataclass_class)

    def __init__(self, **defaults: Any) -> None:
        super().__init__()

        self._stored_defaults = {}

        # Set up the Bunch fields.

        # First, look up internal dataclass attribute names.

        fields_attr: str = getattr(dataclasses, "_FIELDS")
        field_type: Any = getattr(dataclasses, "_FIELD")
        fields: dict[str, dataclasses.Field[Any]] = getattr(
            self, fields_attr, {}
        )

        # Then look up the fields stored in the dataclass.

        for field in fields.values():
            if getattr(field, "_field_type", None) is not field_type:
                continue

            if field.default_factory is dataclasses.MISSING:
                continue

            new_attr = field.default_factory()
            if (
                isinstance(new_attr, Field)
                and (default := defaults.get(field.name, None)) is not None
            ):
                new_attr = new_attr.withDefault(default)
                self._stored_defaults[field.name] = default

            setattr(self, field.name, new_attr)

        self.__post_init__()

    def __post_init__(self) -> None:
        self._parent = None
        self._children = WeakNonHashableSet[Bunch]()
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
        Makes the given Bunch the parent of this one. If None, remove this
        Bunch's parent, if any.

        All the Key, List and Bunch fields defined on this Bunch instance
        will be recursively reparented to the corresponding Key / List / Bunch
        field on the given parent.

        This method is for internal purposes and you will typically not need to
        call it directly.

        Args:
            parent: Either a Bunch that will become this Bunch's parent, or
                None. The parent Bunch must have the same type as this
                Bunch.

        Returns:
            None.

        Note:
            A Bunch and its parent, if any, do not increase each other's
            reference count.
        """

        # Runtime check to affirm the type check of the method.

        if parent is not None:
            if type(self) is not type(parent):
                return

        old_parent = self.parent()
        if old_parent is not None:
            # pylint: disable=protected-access
            old_parent._children.discard(self)

        if parent is None:
            self._parent = None
        else:
            self._parent = weakref.ref(parent)
            # pylint: disable=protected-access
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
        Returns the parent of this Bunch, if any.

        Returns:
            A Bunch instance of the same type as this one, or None.
        """

        # Make the type of self._parent more specific for the purpose of type
        # checking.

        _parent = cast(Optional[weakref.ref[Self]], self._parent)
        return _parent() if _parent is not None else None

    def children(self: Self) -> Iterator[Self]:
        """
        Returns an iterator over the Bunch instances that have this Bunch
        as their parent.

        Returns:
            An iterator over Bunch instances of the same type as this one.
        """

        # Note that we iterate on a copy so that this will not break if a
        # different thread updates the contents during the iteration.

        for child in list(self._children):
            yield cast(Self, child)

    def onUpdateCall(self, callback: Callable[[Any], Any]) -> None:
        """
        Adds a callback to be called whenever this Bunch is updated. A Bunch
        is considered updated when any of its fields is updated.

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

        self._update_notification_callbacks.add(callback)

    def isSet(self) -> bool:
        """
        Indicates whether this Bunch holds any field that is set.

        Returns:
            True if any field set on this Bunch is set, else False.
        """

        return any(field.isSet() for field in self._fields.values())

    def dumpFields(self) -> Iterator[tuple[str, Optional[str]]]:
        """
        Internal.
        """

        if not self.isPrivate():
            for _, field in sorted(self._fields.items()):
                yield from field.dumpFields()

    def restoreField(self, path: str, value: Optional[str]) -> bool:
        """
        Internal.
        """

        if self._PATH_SEPARATOR not in path:
            return False

        field_label, path = path.split(self._PATH_SEPARATOR, 1)
        if self.fieldLabel() != field_label:
            return False

        field_label, *_ = path.split(self._PATH_SEPARATOR, 1)
        if (field := self._fields.get(field_label)) is not None:
            return field.restoreField(path, value)

        return False

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

    def typeHint(self) -> type:
        return type(self)

    def newInstance(
        self: Self, _defaults: Optional[dict[str, Any]] = None
    ) -> Self:
        """
        Internal. Returns a new instance of this Bunch with the same fields.

        Returns:
            A Bunch instance.
        """

        # Make sure the defaults are carried along to the new instance.

        defaults = _defaults.copy() if _defaults else {}
        defaults.update(self._stored_defaults)

        new = self.__class__(**defaults)
        return new

    def withDefault(self: Self, default: Any) -> Self:
        # If a valid override was provided, return that override.

        return (
            default.newInstance(self._stored_defaults)
            if type(default) is type(self)
            else self
        )
