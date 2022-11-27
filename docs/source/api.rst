API Reference
=============

.. autoclass:: sunset.Settings

    .. automethod:: load

    .. automethod:: save

    .. automethod:: newSection

    .. automethod:: getOrCreateSection

    .. automethod:: getSection

    .. automethod:: sections

    .. automethod:: siblings

    .. automethod:: name

    .. automethod:: setName

    .. automethod:: onUpdateCall

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

.. autoclass:: sunset.Bundle

    .. automethod:: onUpdateCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

.. autoclass:: sunset.List

    .. automethod:: iter

    .. automethod:: onUpdateCall

    .. automethod:: parent

    .. automethod:: children

    .. automethod:: setParent

.. autoclass:: sunset.protocols.Serializable

    .. automethod:: fromStr

    .. automethod:: toStr
