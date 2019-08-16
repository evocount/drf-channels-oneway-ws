from django.db.models.signals import (
    post_delete,
    post_save,
    pre_delete,
    pre_save
)
from django.db import transaction
from .utils import groupSendSync

"""
This is heavly inspired from the bindings that existed in channels v1.
"""

CREATE = 'create'
UPDATE = 'update'
DELETE = 'delete'


class BindingMetaClass(type):
    def __new__(cls, clsname, bases, attrs, **kwargs):
        newclass = super().__new__(cls, clsname, bases, attrs, **kwargs)

        if newclass.model is not None:
            newclass.register()

        return newclass


class Binding(object, metaclass=BindingMetaClass):
    """
    Represents a one-way data binding from a django model to channels/groups.
    Outgoing binding sends model events to zero or more groups
    (websockets only).
    """

    model = None
    stream = None
    serializer = None

    # the kwargs the triggering signal (e.g. post_save) was emitted with
    signal_kwargs = None

    @classmethod
    def register(cls):
        """
        Connet model signals.
        """
        pre_save.connect(cls.pre_save_receiver, sender=cls.model)
        post_save.connect(cls.post_save_receiver, sender=cls.model)
        pre_delete.connect(cls.pre_delete_receiver, sender=cls.model)
        post_delete.connect(cls.post_delete_receiver, sender=cls.model)

        cls.model_label = f'{cls.model._meta.app_label.lower()}.{cls.model._meta.object_name.lower()}'

    # Outbound binding

    @classmethod
    def pre_save_receiver(cls, instance, **kwargs):
        creating = instance._state.adding
        cls.pre_change_receiver(instance, CREATE if creating else UPDATE)

    @classmethod
    def post_save_receiver(cls, instance, created, **kwargs):
        # If this is called upon saving a drf serializer which included
        # ManyToMany relationships those will only be available once the
        # commit has finished. As those manytomany fields might be included
        # in the serializer we using for ws messages, let's wait for on_commit.
        transaction.on_commit(
            lambda: cls.post_change_receiver(
                instance,
                CREATE if created else UPDATE,
                **kwargs
            )
        )

    @classmethod
    def pre_delete_receiver(cls, instance, **kwargs):
        cls.pre_change_receiver(instance, DELETE)

    @classmethod
    def post_delete_receiver(cls, instance, **kwargs):
        cls.post_change_receiver(instance, DELETE, **kwargs)

    @classmethod
    def pre_change_receiver(cls, instance, action):
        """
        Entry point for triggering the binding from save signals.
        """
        if action == CREATE:
            group_names = set()
        else:
            group_names = set(cls.group_names(instance))

        if not hasattr(instance, '_binding_group_names'):
            instance._binding_group_names = {}
        instance._binding_group_names[cls] = group_names

    @classmethod
    def post_change_receiver(cls, instance, action, **kwargs):
        """
        Triggers the binding to possibly send to its group.
        """
        old_group_names = instance._binding_group_names[cls]
        if action == DELETE:
            new_group_names = set()
        else:
            new_group_names = set(cls.group_names(instance))

        # if post delete, new_group_names should be []
        self = cls()
        self.instance = instance

        # Django DDP had used the ordering of DELETE, UPDATE then CREATE for good reasons.
        self.send_messages(instance, old_group_names - new_group_names, DELETE, **kwargs)
        self.send_messages(instance, old_group_names & new_group_names, UPDATE, **kwargs)
        self.send_messages(instance, new_group_names - old_group_names, CREATE, **kwargs)

    def send_messages(self, instance, group_names, action, **kwargs):
        """
        Serializes the instance and sends it to all provided group names.
        """
        if not group_names:
            return  # no need to serialize, bail.
        self.signal_kwargs = kwargs
        payload = self.serialize(instance, action)
        if payload == {}:
            return  # nothing to send, bail.

        assert self.stream is not None
        for group_name in group_names:
            groupSendSync(group_name, self.stream, payload)

    @classmethod
    def group_names(cls, instance):
        """
        Returns the iterable of group names to send the object to based on the
        instance and action performed on it.
        """
        raise NotImplementedError()

    def serialize(self, instance, action):
        payload = {
            "action": action,
            "pk": instance.pk,
            "data": self.serialize_data(instance),
            "model": self.model_label,
        }
        return payload

    def serialize_data(self, instance):
        """
        Serializes model data into JSON-compatible types.
        Overwrite this if you do not want to use a django-rest-framework
        serializer.
        """
        assert self.serializer is not None

        return self.serializer(instance).data
