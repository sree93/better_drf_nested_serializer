import unittest

import django
from deepdiff import DeepDiff
from django.conf import settings
from django.test import TestCase

from better_nested_serializer.helpers import combine_related_objects
from test_app.services import normalize_serializer_payload

# Configure Django settings before importing models
if not settings.configured:
    settings.configure(
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
            "test_app",
        ],
        USE_TZ=True,
        SECRET_KEY="test-secret-key",
    )

django.setup()

from django.core.management import call_command

call_command("makemigrations", verbosity=1)
call_command("migrate", verbosity=1)

from test_app.models import Author, Publisher, Blog
from test_app.serializers import (
    BlogSerializerWithAuthorAndPublisher,
    BlogSerializerWithAuthor,
    AuthorWithAllBlogsSerializer,
)


class TestBetterModelSerializerBasic(TestCase):

    def setUp(self):
        # Create test data
        self.author = Author.objects.create(name="Alice", age=30)
        self.publisher = Publisher.objects.create(name="Tech Publications")
        self.blog = Blog.objects.create(
            title="My Blog",
            content="This is blog content",
            author=self.author,
            publisher=self.publisher,
        )

    def test_combine_related_objects(self):
        a = {
            "a": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ],
        }
        b = {
            "a": [
                {"id": 3, "name": "Charlie"},
            ],
            "b": [
                {"id": 3, "name": "Charlie"},
                {"id": 4, "name": "Daniel"},
            ],
        }

        expected_result = {
            "a": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"},
            ],
            "b": [
                {"id": 4, "name": "Daniel"},
                {"id": 3, "name": "Charlie"},
            ],
        }

        self.assertEqual(
            DeepDiff(
                combine_related_objects(a, b),
                expected_result,
                ignore_order=True,
            ),
            {},
            f"""
                    Expected: {expected_result},
                    Got: {a}
            """,
        )

    def test_basic_serialization_returns_expected_dict_and_related_ids(self):
        # Arrange
        serializer = BlogSerializerWithAuthorAndPublisher(instance=self.blog)

        # Act
        data = normalize_serializer_payload(serializer.data)

        expected_response_dict = {
            "object": {
                "author": self.author.id,
                "content": self.blog.content,
                "id": self.blog.id,
                "publisher": self.publisher.id,
                "title": self.blog.title,
            },
            "related_objects": {
                "test_app_author": {
                    self.author.id: {
                        "age": self.author.age,
                        "id": self.author.id,
                        "name": self.author.name,
                    }
                },
                "test_app_publisher": {
                    self.publisher.id: {
                        "id": self.publisher.id,
                        "name": self.publisher.name,
                    }
                },
            },
        }

        self.assertEqual(
            DeepDiff(data, expected_response_dict, ignore_order=True),
            {},
            f"""
                    Expected: {expected_response_dict},
                    Got: {data}
            """,
        )

    def test_serialization_with_none_relationships(self):
        # Test with None relationships
        blog_without_publisher = Blog.objects.create(
            title="Blog without publisher",
            content="Content",
            author=self.author,
            publisher=None,
        )

        serializer = BlogSerializerWithAuthorAndPublisher(
            instance=blog_without_publisher
        )
        data = dict(serializer.data)

        self.assertIsNone(data["object"]["publisher"])

    def test_prohibited_actions(self):
        # Test that prohibited actions raise exceptions
        from better_nested_serializer.exceptions.serializers import ActionProhibited

        with self.assertRaises(ActionProhibited):
            BlogSerializerWithAuthorAndPublisher(data={"title": "test"})

        serializer = BlogSerializerWithAuthorAndPublisher(instance=self.blog)

        with self.assertRaises(ActionProhibited):
            serializer.validate({})

        with self.assertRaises(ActionProhibited):
            serializer.create({})

        with self.assertRaises(ActionProhibited):
            serializer.update(self.blog, {})

    def test_naked_fk_serializer(self):
        serializer = BlogSerializerWithAuthor(instance=self.blog)
        data = normalize_serializer_payload(serializer.data)

        self.assertIn("object", data)
        self.assertIn("related_objects", data)

        related_objects = data["related_objects"]
        self.assertIn("test_app_author", related_objects)
        self.assertNotIn("test_app_publisher", related_objects)

        self.assertEqual(len(related_objects["test_app_author"]), 1)

    def test_many_to_many_field_serializer(self):
        serializer = AuthorWithAllBlogsSerializer(instance=self.author)
        data = normalize_serializer_payload(serializer.data)

        self.assertIn("object", data)
        self.assertIn("related_objects", data)

        related_objects = data["related_objects"]
        self.assertIn("test_app_blog", related_objects)
        self.assertIn("test_app_publisher", related_objects)

        self.assertEqual(len(related_objects["test_app_blog"]), 1)
        self.assertEqual(len(related_objects["test_app_publisher"]), 1)

    def test_list_serialization(self):

        author_2 = Author.objects.create(name="Bob", age=35)

        blog_2 = Blog.objects.create(
            title="Blog 2",
            content="Content 2",
            author=author_2,
            publisher=self.publisher,
        )

        # Arrange
        serializer = BlogSerializerWithAuthorAndPublisher(
            instance=Blog.objects.all(), many=True
        )

        # Act
        data = normalize_serializer_payload(serializer.data)

        expected_response_dict = {
            "object": [
                {
                    "author": self.author.id,
                    "content": self.blog.content,
                    "id": self.blog.id,
                    "publisher": self.publisher.id,
                    "title": self.blog.title,
                },
                {
                    "author": author_2.id,
                    "content": blog_2.content,
                    "id": blog_2.id,
                    "publisher": self.publisher.id,
                    "title": blog_2.title,
                },
            ],
            "related_objects": {
                "test_app_author": {
                    self.author.id: {
                        "age": self.author.age,
                        "id": self.author.id,
                        "name": self.author.name,
                    },
                    author_2.id: {
                        "age": author_2.age,
                        "id": author_2.id,
                        "name": author_2.name,
                    },
                },
                "test_app_publisher": {
                    self.publisher.id: {
                        "id": self.publisher.id,
                        "name": self.publisher.name,
                    }
                },
            },
        }

        diff = DeepDiff(data, expected_response_dict, ignore_order=True)
        self.assertEqual(
            diff,
            {},
            f"""
                    Expected: {expected_response_dict},
                    Got: {data}
            """,
        )


if __name__ == "__main__":

    unittest.main()
