# better-nested-serializer

A tiny add‑on for Django REST Framework (DRF) that makes nested data smaller and easier to cache.

Simple idea:
- In the main object, send only IDs for nested fields.
- Put the full nested objects in one place called "related_objects".

This avoids repeating the same nested object many times and keeps responses small.


## What the output looks like
When you use `BetterModelSerializer`, you get a response shaped like this:

```json
{
  "object": {
    "id": 10,
    "title": "My Blog Post",
    "author": 3,
    "publisher": 2
  },
  "related_objects": {
    "test_app_author": {
      "3": { "id": 3, "name": "Ada" }
    },
    "test_app_publisher": {
      "2": { "id": 2, "name": "Tech Books" }
    }
  }
}
```

Notes:
- Keys in `related_objects` look like `<app_label>_<model_name>` (for example: `test_app_author`).
- Each value is a map of `id -> full object`.
- If a nested serializer also uses `BetterModelSerializer`, its own `related_objects` get merged in.


## Why this is helpful
- Smaller payloads (no duplicated nested objects)
- Easy client caching (each related object appears once by ID)
- Clean split between the main object and related data


## Requirements
- Python 3.12+
- Django REST Framework 3.16+
- Django (a version supported by your DRF)


## Install
```text
pip install better-nested-serializer
```


## Quick start
1) Import the base class in your DRF serializers file:
```text
from serializers.model_serializer import BetterModelSerializer
```

2) Create your serializers. You can mix plain DRF serializers and `BetterModelSerializer`:
```text
from rest_framework import serializers
from serializers.model_serializer import BetterModelSerializer
from .models import Author, Blog, Publisher

class PublisherSerializer(BetterModelSerializer):
    class Meta:
        model = Publisher
        fields = "__all__"

class AuthorSerializer(serializers.ModelSerializer):  # plain DRF serializer is fine
    class Meta:
        model = Author
        fields = "__all__"

class BlogSerializer(BetterModelSerializer):
    author = AuthorSerializer(read_only=True)        # nested: DRF serializer
    publisher = PublisherSerializer(read_only=True)  # nested: BetterModelSerializer

    class Meta:
        model = Blog
        fields = "__all__"
```

3) Use it anywhere you serialize a model instance (view, viewset, etc.):
```text
blog = Blog.objects.select_related("author", "publisher").get(pk=10)
serialized = BlogSerializer(blog)
Response(serialized.data)
```

Output example:
```json
{
  "object": {
    "id": 10,
    "title": "My Blog Post",
    "author": 3,
    "publisher": 2
  },
  "related_objects": {
    "test_app_author": {
      "3": { "id": 3, "name": "Ada" }
    },
    "test_app_publisher": {
      "2": { "id": 2, "name": "Tech Books" }
    }
  }
}
```


## Reverse relations (lists)
You can also serialize reverse relations (like `author.blog_set`). Example:
```text
class BlogWithPublisherSerializer(BetterModelSerializer):
    publisher = PublisherSerializer(read_only=True)
    class Meta:
        model = Blog
        fields = "__all__"

class AuthorWithBlogsSerializer(BetterModelSerializer):
    blogs = BlogWithPublisherSerializer(many=True, read_only=True, source="blog_set")
    class Meta:
        model = Author
        fields = "__all__"
```

Sample output:
```json
{
  "object": {
    "id": 3,
    "name": "Ada",
    "blogs": [10, 11, 12]
  },
  "related_objects": {
    "test_app_blog": {
      "10": { "id": 10, "title": "My Blog Post", "publisher": 2 },
      "11": { "id": 11, "title": "Another Post", "publisher": 2 },
      "12": { "id": 12, "title": "Last Post", "publisher": 5 }
    },
    "test_app_publisher": {
      "2": { "id": 2, "name": "Tech Books" },
      "5": { "id": 5, "name": "Daily News" }
    }
  }
}
```


## How it works (in short)
- The serializer returns 2 things: the main object and a map of related objects.
- Nested fields become IDs in the main object.
- The full nested objects are grouped under `related_objects` by their IDs.
- If a nested serializer is also `BetterModelSerializer`, it adds its related data into the same `related_objects` block.


## Important notes
- Output only: this serializer is read‑only. It does not support `data=...`, `create`, `update`, or `validate`.
- Use `read_only=True` for nested fields.
- You can mix plain DRF serializers and `BetterModelSerializer` without problems.


## FAQ
- Can I POST with this serializer?
  - No. It’s for output only.

- Do I need to change my models?
  - No. Use your existing Django models.

- What about deep nesting?
  - Works fine. Each level adds its objects to `related_objects`.


## License
MIT (or your project’s license).
