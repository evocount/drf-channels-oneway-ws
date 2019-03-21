from rest_framework.utils.encoders import JSONEncoder
import json


class DRFJsonConsumerMixinAsync:
    """
    Use this mixin on your consumers to encode json using
    django-rest-framework's encoder and to enable sending from bindings.
    """
    @classmethod
    async def encode_json(cls, content):
        return json.dumps(content, cls=JSONEncoder)

    async def group_send_encoded(self, data):
        await self.send(text_data=data['content'])
