import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from notifications.models import Notification

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """Real-time notifications"""
    
    async def connect(self):
        await self.accept()
        
        user = self.scope.get('user')
        if user and user.is_authenticated:
            self.room_group_name = f'notifications_{user.id}'
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to notifications'
            }))
        else:
            await self.close()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
    
    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'notification': event['notification']
        }))


class ChatConsumer(AsyncWebsocketConsumer):
    """Real-time chat"""
    
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data['message']
        
        message = await self.save_message(message_content)
        
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message_content,
                'sender': message['sender'],
                'created_at': message['created_at']
            }
        )
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender': event['sender'],
            'created_at': event['created_at']
        }))
    
    @database_sync_to_async
    def save_message(self, content):
        user = self.scope['user']
        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(
            conversation=conversation,
            sender=user,
            content=content
        )
        return {
            'id': message.id,
            'sender': user.username,
            'created_at': message.created_at.isoformat()
        }