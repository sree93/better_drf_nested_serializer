import dataclasses
from typing import Type, Dict, Iterable

from deepmerge import always_merger
from django.db.models import Model
from rest_framework import serializers
from rest_framework.relations import PKOnlyObject


@dataclasses.dataclass
class NestedData:
    model_class: Type[Model]
    serializer_class: Type[serializers.Serializer]
    kwargs: dict


class NestedDataHelper:

    def __init__(self):
        self._mapping__field_info: Dict[str, NestedData] = {}
        self._model_cache: Dict[
            Type[Model], Iterable[Model] | Iterable[PKOnlyObject]
        ] = {}

    def get_model_class(self, field_name):
        return self._mapping__field_info[field_name].model_class

    def get_serializer_class(self, field_name):
        return self._mapping__field_info[field_name].serializer_class

    def get_serializer_kwargs(self, field_name):
        return self._mapping__field_info[field_name].kwargs

    def get_serializer(self, field_name):
        return self.get_serializer_class(field_name)(
            **self.get_serializer_kwargs(field_name)
        )

    def get_model_instances(self, model_class):
        if model_class not in self._model_cache:
            self._model_cache[model_class] = model_class.objects.all()
        return self._model_cache[model_class]

    def append_to_cache(self, model_class, model_instances):
        self._model_cache[model_class] = model_instances

    def items(self):
        yield from self._mapping__field_info.items()

    def add(
        self,
        field_name: str,
        model_class: Type[Model],
        serializer_class: Type[serializers.Serializer],
        kwargs: Dict = None,
        append_to_instance_cache: Iterable[Model] | Iterable[PKOnlyObject] = None,
    ):
        if kwargs is None:
            kwargs = {}

        self._mapping__field_info[field_name] = NestedData(
            model_class, serializer_class, kwargs
        )
        if append_to_instance_cache:
            self.append_to_cache(model_class, append_to_instance_cache)


def combine_related_objects(
    related_objects: Dict[str, Dict], child_related_objs: Dict[str, dict]
):
    return always_merger.merge(related_objects, child_related_objs)
