API Reference
=============

Settings
--------

.. autoclass:: sunset.Settings

    .. automethod:: load

    .. automethod:: save

    .. automethod:: derive

    .. automethod:: deriveAs

    .. automethod:: name

    .. automethod:: setName

    .. automethod:: onUpdateCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

    .. automethod:: siblings

Key
---

.. autoclass:: sunset.Key

    .. automethod:: set

    .. automethod:: get

    .. automethod:: isSet

    .. automethod:: clear

    .. automethod:: onValueChangeCall

    .. automethod:: onUpdateCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

Bundle
------

.. autoclass:: sunset.Bundle

    .. automethod:: derive

    .. automethod:: onUpdateCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

List
----

.. autoclass:: sunset.List

    .. automethod:: iter

    .. automethod:: onUpdateCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

protocols.Serializable
----------------------

.. autoclass:: sunset.protocols.Serializable

    .. automethod:: fromStr

    .. automethod:: toStr
