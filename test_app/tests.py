import unittest

import django
from django.conf import settings
from django.test import TestCase

# Configure Django settings before importing models
if not settings.configured:
    settings.configure(
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME'  : ':memory:',
            }
        },
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'test_app',
        ],
        USE_TZ=True,
        SECRET_KEY='test-secret-key',
    )

django.setup()

from django.core.management import call_command

call_command('makemigrations', verbosity=1)
call_command('migrate', verbosity=1)

from test_app.models import Author, Publisher, Blog
from test_app.serializers import BlogSerializerWithAuthorAndPublisher, BlogSerializerWithAuthor, \
    AuthorWithAllBlogsSerializer


class TestBetterModelSerializerBasic(TestCase):

    def setUp(self):
        # Create test data
        self.author = Author.objects.create(name="Alice", age=30)
        self.publisher = Publisher.objects.create(name="Tech Publications")
        self.blog = Blog.objects.create(
            title="My Blog",
            content="This is blog content",
            author=self.author,
            publisher=self.publisher
        )

    def test_basic_serialization_returns_expected_dict_and_related_ids(self):
        # Arrange
        serializer = BlogSerializerWithAuthorAndPublisher(instance=self.blog)

        # Act
        data = serializer.data

        # Assert
        self.assertIn('object', data)
        self.assertIn('related_objects', data)

        # Check main object data
        main_data = data['object']
        self.assertEqual(main_data['title'], "My Blog")
        self.assertEqual(main_data['content'], "This is blog content")

        # Check nested serializer data
        related_data = data['related_objects']
        self.assertEqual(len(related_data['test_app_author']), 1)
        self.assertEqual(related_data['test_app_author'][self.author.id]['name'], "Alice")
        self.assertEqual(related_data['test_app_author'][self.author.id]['age'], 30)

    def test_serialization_with_none_relationships(self):
        # Test with None relationships
        blog_without_publisher = Blog.objects.create(
            title="Blog without publisher",
            content="Content",
            author=self.author,
            publisher=None
        )

        serializer = BlogSerializerWithAuthorAndPublisher(instance=blog_without_publisher)
        data = serializer.data

        self.assertIsNone(data['object']['publisher'])

    def test_prohibited_actions(self):
        # Test that prohibited actions raise exceptions
        from exceptions.serializers import ActionProhibited

        with self.assertRaises(ActionProhibited):
            BlogSerializerWithAuthorAndPublisher(data={'title': 'test'})

        serializer = BlogSerializerWithAuthorAndPublisher(instance=self.blog)

        with self.assertRaises(ActionProhibited):
            serializer.validate({})

        with self.assertRaises(ActionProhibited):
            serializer.create({})

        with self.assertRaises(ActionProhibited):
            serializer.update(self.blog, {})

    def test_naked_fk_serializer(self):
        serializer = BlogSerializerWithAuthor(instance=self.blog)
        data = serializer.data

        self.assertIn('object', data)
        self.assertIn('related_objects', data)

        related_objects = data['related_objects']
        self.assertIn('test_app_author', related_objects)
        self.assertNotIn('test_app_publisher', related_objects)

        self.assertEqual(len(related_objects['test_app_author']), 1)


    def test_many_to_many_field_serializer(self):
        serializers = AuthorWithAllBlogsSerializer(instance=self.author)
        data = serializers.data

        self.assertIn('object', data)
        self.assertIn('related_objects', data)

        related_objects = data['related_objects']
        self.assertIn('test_app_blog', related_objects)
        self.assertIn('test_app_publisher', related_objects)

        self.assertEqual(len(related_objects['test_app_blog']), 1)
        self.assertEqual(len(related_objects['test_app_publisher']), 1)

if __name__ == "__main__":

    unittest.main()
