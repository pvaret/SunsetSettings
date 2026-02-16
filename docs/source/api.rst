API Reference
=============

.. autoclass:: sunset.Settings

    .. automethod:: load

    .. automethod:: save

    .. automethod:: autosave

    .. automethod:: addLayer

    .. automethod:: getOrAddLayer

    .. automethod:: getLayer

    .. automethod:: layers

    .. automethod:: layerName

    .. automethod:: setLayerName

    .. automethod:: onUpdateCall

    .. automethod:: skipOnSave

.. autoclass:: sunset.Key

    .. automethod:: set

    .. automethod:: get

    .. automethod:: isSet

    .. automethod:: fallback

    .. automethod:: updateValue

    .. automethod:: clear

    .. automethod:: setValidator

    .. automethod:: onValueChangeCall

    .. automethod:: onUpdateCall

    .. automethod:: skipOnSave

.. autoclass:: sunset.Bunch

    .. automethod:: onUpdateCall

    .. automethod:: skipOnSave

.. autoclass:: sunset.List

    .. automethod:: iter

    .. automethod:: appendOne

    .. automethod:: insertOne

    .. automethod:: onUpdateCall

    .. automethod:: skipOnSave

.. autoclass:: sunset.AutoSaver

    .. automethod:: doLoad

    .. automethod:: doSave

    .. automethod:: saveIfNeeded

.. autoclass:: sunset.AutoLoader

    .. automethod:: doLoad

.. autoclass:: sunset.Serializer

    .. automethod:: toStr

    .. automethod:: fromStr

.. autoclass:: sunset.Serializable

    .. automethod:: toStr

    .. automethod:: fromStr
