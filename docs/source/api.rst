API Reference
=============

.. autoclass:: sunset.Settings

    .. automethod:: load

    .. automethod:: save

    .. automethod:: newSection

    .. automethod:: getOrCreateSection

    .. automethod:: getSection

    .. automethod:: sections

    .. automethod:: sectionName

    .. automethod:: setSectionName

    .. automethod:: onUpdateCall

.. autoclass:: sunset.Key

    .. automethod:: set

    .. automethod:: get

    .. automethod:: isSet

    .. automethod:: clear

    .. automethod:: onValueChangeCall

    .. automethod:: onUpdateCall

.. autoclass:: sunset.Bundle

    .. automethod:: onUpdateCall

.. autoclass:: sunset.List

    .. automethod:: iter

    .. automethod:: appendOne

    .. automethod:: insertOne

    .. automethod:: onUpdateCall

.. autoclass:: sunset.AutoSaver

    .. automethod:: doSave

    .. automethod:: saveIfNeeded

.. autoclass:: sunset.Serializable

    .. automethod:: toStr

    .. automethod:: fromStr
