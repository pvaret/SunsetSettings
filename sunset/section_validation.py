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
        " instantiated directly, which is invalid; use {function}"
        " instead!"
    )

    for name, attr in vars(cls).items():
        if isinstance(attr, Section):
            raise ValueError(
                err_msg.format(
                    clsname=cls.__name__,
                    name=name,
                    type="Section",
                    function="sunset.NewSection",
                )
            )
        if isinstance(attr, List):
            raise ValueError(
                err_msg.format(
                    clsname=cls.__name__,
                    name=name,
                    type="List",
                    function="sunset.NewSectionList or sunset.NewSettingList",
                )
            )
        if isinstance(attr, Setting):
            raise ValueError(
                err_msg.format(
                    clsname=cls.__name__,
                    name=name,
                    type="Setting",
                    function="sunset.NewSetting",
                )
            )
