import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    """Real vaqtda bildirishnomalar uchun WebSocket consumer"""

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'notifications_{self.user.id}'

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

        # Ulanganda o'qilmagan sonini yuborish
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('action') == 'mark_read':
                await self.mark_all_read()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': 0,
                }))
        except Exception:
            pass

    async def notification_message(self, event):
        await self.send(text_data=json.dumps({
            'type':    'notification',
            'title':   event.get('title', ''),
            'message': event.get('message', ''),
            'icon':    event.get('icon', 'fa-bell'),
            'color':   event.get('color', 'cyan'),
            'url':     event.get('url', '#'),
        }))
        count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': count,
        }))

    @database_sync_to_async
    def get_unread_count(self):
        # Lazy import — settings yuklanganidan keyin
        from core.models import Notification
        return Notification.objects.filter(
            user=self.user, is_read=False
        ).count()

    @database_sync_to_async
    def mark_all_read(self):
        from core.models import Notification
        Notification.objects.filter(
            user=self.user, is_read=False
        ).update(is_read=True)
