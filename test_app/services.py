from collections.abc import Mapping, Iterable


def _to_plain(value):
    # Recursively convert DRF ReturnDict/ReturnList/OrderedDict to plain dict/list
    # and make basic Python types only.
    if isinstance(value, Mapping):
        return {k: _to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]
    return value


def map_list_by_id(items):
    # Turn a list of objects with 'id' into a dict keyed by id
    out = {}
    for item in items:
        plain = _to_plain(item)
        item_id = plain.get("id")
        if item_id is None:
            continue
        out[int(item_id)] = plain
    return out


def normalize_serializer_payload(data):
    """
    Enforce the contract expected by tests:
    {
      "object": dict | list[dict],
      "related_objects": {
         "<app_model>": { <id>: { ... }, ... },
         ...
      }
    }
    """
    payload = _to_plain(data)

    # Normalize related_objects: convert inner lists to dicts keyed by id, ensure ids are ints
    related = payload.get("related_objects")
    if isinstance(related, Mapping):
        fixed_related = {}
        for model_key, value in related.items():
            if isinstance(value, Mapping):
                # Ensure keys are ints
                fixed_related[model_key] = {
                    int(k): _to_plain(v) for k, v in value.items()
                }
            elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                fixed_related[model_key] = map_list_by_id(value)
            else:
                fixed_related[model_key] = _to_plain(value)
        payload["related_objects"] = fixed_related

    # Ensure "object" is plain dict or list of dicts
    obj = payload.get("object")
    if obj is not None:
        payload["object"] = _to_plain(obj)

    return payload
