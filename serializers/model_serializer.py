from django.db.models.manager import BaseManager
from rest_framework import serializers
from rest_framework.fields import SkipField
from rest_framework.relations import PKOnlyObject, PrimaryKeyRelatedField
from rest_framework.serializers import (
    ListSerializer,
    LIST_SERIALIZER_KWARGS_REMOVE,
    LIST_SERIALIZER_KWARGS,
)
from rest_framework.utils.serializer_helpers import ReturnDict

from exceptions.serializers import ActionProhibited
from helpers import NestedDataHelper, combine_related_objects
from serializers.list_serializer import BetterListSerializer


class BetterModelSerializer(serializers.ModelSerializer):

    def __init__(self, instance=None, is_nested=False, **kwargs):
        self.is_nested = is_nested
        self.kwargs = kwargs
        if "data" in kwargs:
            raise ActionProhibited(self.__class__, action="Deserialization")
        super().__init__(instance=instance, **kwargs)

    @classmethod
    def many_init(cls, *args, **kwargs):
        """
        This method implements the creation of a `ListSerializer` parent
        class when `many=True` is used. You can customize it if you need to
        control which keyword arguments are passed to the parent, and
        which are passed to the child.

        Note that we're over-cautious in passing most arguments to both parent
        and child classes in order to try to cover the general case. If you're
        overriding this method you'll probably want something much simpler, eg:

        @classmethod
        def many_init(cls, *args, **kwargs):
            kwargs['child'] = cls()
            return CustomListSerializer(*args, **kwargs)
        """
        list_kwargs = {}
        for key in LIST_SERIALIZER_KWARGS_REMOVE:
            value = kwargs.pop(key, None)
            if value is not None:
                list_kwargs[key] = value
        list_kwargs["child"] = cls(*args, **kwargs)
        list_kwargs.update(
            {
                key: value
                for key, value in kwargs.items()
                if key in LIST_SERIALIZER_KWARGS
            }
        )
        meta = getattr(cls, "Meta", None)
        list_serializer_class = getattr(
            meta, "list_serializer_class", cls.get_default_list_serializer_class()
        )
        return list_serializer_class(*args, **list_kwargs)

    @classmethod
    def get_default_list_serializer_class(cls):
        return BetterListSerializer

    def validate(self, attrs):
        raise ActionProhibited(self.__class__, action="Validation")

    def create(self, validated_data):
        raise ActionProhibited(self.__class__, action="Creation")

    def update(self, instance, validated_data):
        raise ActionProhibited(self.__class__, action="Update")

    def to_representation(self, instance):
        primary_object = {}
        fields = self._readable_fields

        nested_helper = NestedDataHelper()

        for field in fields:
            try:
                attribute = field.get_attribute(instance)
            except SkipField:
                continue

            # We skip `to_representation` for `None` values so that fields do
            # not have to explicitly deal with that case.
            #
            # For related fields with `use_pk_only_optimization` we need to
            # resolve the pk value.
            check_for_none = (
                attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            )
            if check_for_none is None:
                primary_object[field.field_name] = None
            else:
                if isinstance(field, serializers.ModelSerializer):
                    primary_object[field.field_name] = PrimaryKeyRelatedField(
                        queryset=field.Meta.model.objects.all()
                    ).to_representation(attribute)

                    nested_helper.add(
                        field_name=field.field_name,
                        model_class=field.Meta.model,
                        serializer_class=field.__class__,
                        # kwargs=field.kwargs,
                        append_to_instance_cache=[attribute],
                    )

                elif isinstance(field, ListSerializer) and isinstance(
                    field.child, serializers.ModelSerializer
                ):

                    if isinstance(attribute, BaseManager):
                        attribute = attribute.all()

                    primary_object[field.field_name] = PrimaryKeyRelatedField(
                        queryset=field.child.Meta.model.objects.all(), many=True
                    ).to_representation(attribute)

                    nested_helper.add(
                        field_name=field.field_name,
                        model_class=field.child.Meta.model,
                        serializer_class=field.child.__class__,
                        # kwargs=field.kwargs,
                        append_to_instance_cache=attribute,
                    )
                else:
                    primary_object[field.field_name] = field.to_representation(
                        attribute
                    )

        related_objects = {}

        for field_name, field_info in nested_helper.items():
            model_name = f"{field_info.model_class._meta.app_label}_{field_info.model_class._meta.model_name}"

            serialized_data = field_info.serializer_class(
                many=True, **field_info.kwargs
            ).to_representation(
                data=nested_helper.get_model_instances(field_info.model_class)
            )
            normalized_serialized_data = []

            if issubclass(field_info.serializer_class, BetterModelSerializer):
                related_objects = combine_related_objects(
                    related_objects, serialized_data["related_objects"]
                )
                normalized_serialized_data.extend(serialized_data["object"])
            else:
                normalized_serialized_data.extend(serialized_data)

            related_objects[model_name] = {
                _["id"]: _ for _ in normalized_serialized_data
            }

        return {"object": primary_object, "related_objects": related_objects}

    @property
    def data(self):
        ret = super().data
        return ReturnDict(ret, serializer=self)
