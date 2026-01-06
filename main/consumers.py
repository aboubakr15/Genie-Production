import json 
from channels.generic.websocket import AsyncWebsocketConsumer 
from django.contrib.auth.models import User 
from .models import Notification 

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = f'notifications_{self.scope["user"].id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name) 
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name) 

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        receiver = User.objects.get(id=data['receiver_id']) 
        
        notification = Notification.objects.create( 
            sender=self.scope['user'], 
            receiver=receiver, 
            message=data['message'],
            notification_type = 0,
            )
        
        await self.channel_layer.group_send( 
            f'notifications_{receiver.id}', 
            { 'type': 'send_notification', 
            'message': data['message'],
            'id': data['id'],
            'read': data['read'],
            'state': data['state']
            },
        )

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
                'message': event['message'],
                'id': event['id'],
                'read': event['read'],
                'state': event['state']
                }))
