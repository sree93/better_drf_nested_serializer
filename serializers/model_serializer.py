from django.db.models.manager import BaseManager
from rest_framework import serializers
from rest_framework.fields import SkipField
from rest_framework.relations import PKOnlyObject, PrimaryKeyRelatedField
from rest_framework.serializers import ListSerializer

from exceptions.serializers import ActionProhibited
from helpers import NestedDataHelper


class BetterModelSerializer(serializers.ModelSerializer):

    def __init__(self, instance=None, is_nested=False, **kwargs):
        self.is_nested = is_nested
        self.kwargs = kwargs
        if 'data' in kwargs:
            raise ActionProhibited(self.__class__, action='Deserialization')
        super().__init__(instance=instance, **kwargs)

    def validate(self, attrs):
        raise ActionProhibited(self.__class__, action='Validation')

    def create(self, validated_data):
        raise ActionProhibited(self.__class__, action='Creation')

    def update(self, instance, validated_data):
        raise ActionProhibited(self.__class__, action='Update')

    def to_representation(self, instance):
        ret = {}
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
            check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
            if check_for_none is None:
                ret[field.field_name] = None
            else:
                if isinstance(field, serializers.ModelSerializer):
                    ret[field.field_name] = PrimaryKeyRelatedField(
                        queryset=field.Meta.model.objects.all()
                    ).to_representation(attribute)

                    nested_helper.add(
                        field_name=field.field_name,
                        model_class=field.Meta.model,
                        serializer_class=field.__class__,
                        # kwargs=field.kwargs,
                        append_to_instance_cache=[attribute]
                    )

                elif isinstance(field, ListSerializer) and isinstance(field.child, serializers.ModelSerializer):

                    if isinstance(attribute, BaseManager):
                        attribute = attribute.all()

                    ret[field.field_name] = PrimaryKeyRelatedField(
                        queryset=field.child.Meta.model.objects.all(),
                        many=True
                    ).to_representation(attribute)

                    nested_helper.add(
                        field_name=field.field_name,
                        model_class=field.child.Meta.model,
                        serializer_class=field.child.__class__,
                        # kwargs=field.kwargs,
                        append_to_instance_cache=attribute
                    )
                else:
                    ret[field.field_name] = field.to_representation(attribute)

        related_objects = {}

        for field_name, field_info in nested_helper.items():
            model_name = f'{field_info.model_class._meta.app_label}_{field_info.model_class._meta.model_name}'

            serialized_data = field_info.serializer_class(
                many=True, **field_info.kwargs
            ).to_representation(
                data=nested_helper.get_model_instances(field_info.model_class)
            )
            normalized_serialized_data = []
            for item in serialized_data:
                if isinstance(item, tuple):
                    for key, value in item[1].items():
                        related_objects.setdefault(key, {}).update(value)
                    normalized_serialized_data.append(item[0])
                else:
                    normalized_serialized_data.append(item)

            related_objects[model_name] = {_['id']: _ for _ in normalized_serialized_data}

        return ret, related_objects

    @property
    def data(self):
        main_data, related_data = self.to_representation(self.instance)
        return {
            'object'         : main_data,
            'related_objects': related_data
        }
