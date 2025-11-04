from django.db import models
from rest_framework import serializers
from rest_framework.utils.serializer_helpers import ReturnDict

from helpers import combine_related_objects


class BetterListSerializer(serializers.ListSerializer):
    def to_representation(self, data):
        """
        List of object instances -> List of dicts of primitive datatypes.
        """
        from serializers.model_serializer import BetterModelSerializer

        # Dealing with nested relationships, data can be a Manager,
        # so, first get a queryset from the Manager if needed
        iterable = data.all() if isinstance(data, models.manager.BaseManager) else data

        primary_objects = []

        related_objects = {}

        for item in iterable:
            child_data = self.child.to_representation(item)

            if isinstance(self.child, BetterModelSerializer):
                """
                Here we are dealing with nested relationships, of format:
                    (<primary_object_dict>, <related_objects_dict>)
                """
                child_primary_obj = child_data["object"]
                child_related_objs = child_data["related_objects"]
                primary_objects.append(child_primary_obj)

                related_objects = combine_related_objects(
                    related_objects, child_related_objs
                )
            else:
                primary_objects.append(child_data)
        return {"object": primary_objects, "related_objects": related_objects}

    @property
    def data(self):
        ret = self.to_representation(self.instance)
        return ReturnDict(ret, serializer=self)
