API Reference
=============

sunset.Settings
---------------

.. autoclass:: sunset.Settings

    .. automethod:: load

    .. automethod:: save

    .. automethod:: derive

    .. automethod:: deriveAs

    .. automethod:: name

    .. automethod:: setName

    .. automethod:: onSettingModifiedCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

    .. automethod:: siblings

sunset.Section
--------------

.. autofunction:: sunset.NewSection

.. autoclass:: sunset.Section

    .. automethod:: derive

    .. automethod:: onSettingModifiedCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

sunset.Setting
--------------

.. autofunction:: sunset.NewSetting

.. autoclass:: sunset.Setting

    .. automethod:: set

    .. automethod:: get

    .. automethod:: isSet

    .. automethod:: clear

    .. automethod:: onValueChangeCall

    .. automethod:: onSettingModifiedCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

sunset.List
-----------

.. autofunction:: sunset.NewList

.. autoclass:: sunset.List

    .. automethod:: iterAll

    .. automethod:: onSettingModifiedCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

sunset.protocols.Serializable
-----------------------------

.. autoclass:: sunset.protocols.Serializable

    .. automethod:: fromStr

    .. automethod:: toStr
