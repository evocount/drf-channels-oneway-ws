# DRF channels one-way WS

Simple one-way bindings for django-channels with some specific support for django-rest-framework serializers and websockets. I.e. enrich your existing API with push notifications.

## Installation

* `pipenv install drf-channels-oneway-ws` or `pip install drf-channels-oneway-ws`

## Usage

```python
from django.db import models
from rest_framework import serializers
from channels_oneway.bindings import Binding

class Family(models.Model):
    name = models.CharField(max_length=255)

class Bird(models.Model):
    name = models.CharField(max_length=255)
    family = models.ForeignKey('Family', models.CASCADE)


class BirdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ('__all__')


class BirdBinding(Binding):
    model = Bird
    stream = 'birds'
    serializer = BirdSerializer

    @classmethod
    def group_names(cls, instance):
        return [instance.family.name]

class FamilyBinding(Binding):
    """
    example of a binding not using a drf serializer
    """
    model = Family
    stream = 'families'

    @classmethod
    def group_names(cls, instance):
        return [instance.name]

    def serialize_data(self, instance):
        return {'id': instance.id, 'name': instance.name}
```


## Contributing

### Installation

* `git clone git@github.com:evocount/drf-channels-oneway-ws.git`
* `cd python-set-ings`
* `pipenv install --dev`

### Running tests

* `pipenv run pytest --cov`

## License

This project is licensed under the [MIT License](LICENSE.md).
