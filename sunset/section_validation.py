from typing import Type

from .list import List
from .section import Section
from .setting import Setting


def validateElementsAreFields(cls: Type[Section]) -> None:
    """
    Validate that the user is holding SunsetSettings right.

    It is an error to add a Setting instance, a Section instance or a List
    instance directly to a Section or a Settings definition. If the users does
    so, then the instance will be shared across *all* instances of that Section
    or Settings class.

    Args:
        cls: a Section class.

    Returns:
        None.

    Raises:
        ValueError if the user unwittingly added a Setting, List or Section
            instance to their Section/Settings definition.
    """

    err_msg = (
        "In the definition of '{clsname}', '{name}' is a {type} that was"
        " instantiated directly, which is invalid; use sunset.New{type}"
        " instead!"
    )

    for name, attr in vars(cls).items():
        if isinstance(attr, Section):
            raise ValueError(
                err_msg.format(name=name, type="Section", clsname=cls.__name__)
            )
        if isinstance(attr, List):
            raise ValueError(
                err_msg.format(name=name, type="List", clsname=cls.__name__)
            )
        if isinstance(attr, Setting):
            raise ValueError(
                err_msg.format(name=name, type="Setting", clsname=cls.__name__)
            )
