from asgiref.sync import async_to_sync
from rest_framework.utils.encoders import JSONEncoder
from channels.layers import get_channel_layer
import json


channel_layer = get_channel_layer()


async def groupWsSend(group, stream, payload):
    """
    …
    """
    await channel_layer.group_send(
        group,
        {
            'type': 'group.send_encoded',
            'content': json.dumps({
                'stream': stream,
                'payload': payload
            }, cls=JSONEncoder)
        }
    )


def groupWsSendSync(group, stream, payload):
    async_to_sync(groupWsSend)(
        group,
        stream,
        payload
    )
