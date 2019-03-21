from django.contrib.auth import get_user_model
from django.conf.urls import url
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from asgiref.sync import sync_to_async
from channels_oneway.bindings import Binding
from channels_oneway.mixins import DRFJsonConsumerMixinAsync
import pytest

User = get_user_model()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_binding():
    class TestBinding(Binding):
        model = User
        stream = 'users'

        @classmethod
        def group_names(cls, instance):
            return ['test']

        def serialize_data(self, instance):
            return {'id': instance.id, 'username': instance.username}

    class TestConsumer(AsyncJsonWebsocketConsumer, DRFJsonConsumerMixinAsync):
        async def connect(self):
            await self.channel_layer.group_add('test', self.channel_name)
            await self.accept()

        async def disconnect(self, close_code):
            await self.channel_layer.group_discard('test', self.channel_name)

    application = URLRouter([
        url(r"^testws/$", TestConsumer),
    ])

    communicator = WebsocketCommunicator(application, "/testws/")
    connected, subprotocol = await communicator.connect()
    assert connected

    user = await sync_to_async(User.objects.create)(username='root')

    response = await communicator.receive_json_from()

    assert response == {
        'stream': 'users',
        'payload': {
            'action': 'create',
            'data': {'id': 1, 'username': 'root'},
            'model': 'auth.user',
            'pk': 1
        }
    }

    user.username = 'SuperUser'

    await sync_to_async(user.save)()

    response = await communicator.receive_json_from()

    assert response == {
        'stream': 'users',
        'payload': {
            'action': 'update',
            'data': {'id': 1, 'username': 'SuperUser'},
            'model': 'auth.user',
            'pk': 1
        }
    }

    await sync_to_async(user.delete)()

    response = await communicator.receive_json_from()

    assert response == {
        'stream': 'users',
        'payload': {
            'action': 'delete',
            'data': {'id': 1, 'username': 'SuperUser'},
            'model': 'auth.user',
            'pk': 1
        }
    }

    await communicator.disconnect()
