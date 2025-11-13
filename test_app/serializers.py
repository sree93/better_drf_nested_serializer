# Create specific serializers for testing
from rest_framework import serializers

from better_nested_serializer.serializers.model_serializer import BetterModelSerializer
from test_app.models import Author, Blog, Publisher


class PublisherSerializer(BetterModelSerializer):
    class Meta:
        model = Publisher
        fields = '__all__'


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = '__all__'


class BlogSerializerWithAuthorAndPublisher(BetterModelSerializer):
    author = AuthorSerializer(read_only=True)
    publisher = PublisherSerializer(read_only=True)

    class Meta:
        model = Blog
        fields = '__all__'


class BlogSerializerWithAuthor(BetterModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Blog
        fields = '__all__'

class BlogSerializerWithPublisher(BetterModelSerializer):
    publisher = PublisherSerializer(read_only=True)

    class Meta:
        model = Blog
        fields = '__all__'


class AuthorWithAllBlogsSerializer(BetterModelSerializer):
    blogs = BlogSerializerWithPublisher(many=True, read_only=True, source='blog_set')

    class Meta:
        model = Author
        fields = '__all__'
