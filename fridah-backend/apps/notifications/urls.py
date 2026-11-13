from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.NotificationListView.as_view(), name='notification_list'),
    path('notifications/<uuid:id>/read/', views.NotificationMarkReadView.as_view(), name='notification_read'),
    path('notifications/read-all/', views.NotificationMarkAllReadView.as_view(), name='notification_read_all'),
    path('notifications/unread-count/', views.NotificationUnreadCountView.as_view(), name='notification_unread_count'),
    path('notification-preferences/', views.NotificationPreferenceView.as_view(), name='notification_preferences'),
]

# FRIDAH Chat
from . import messaging_views as chat_views
urlpatterns += [
    path('chat/threads/', chat_views.MessageThreadListView.as_view(), name='chat_thread_list'),
    path('chat/threads/group/', chat_views.PropertyGroupThreadView.as_view(), name='chat_thread_group'),
    path('chat/threads/<uuid:thread_id>/messages/', chat_views.MessageListView.as_view(), name='chat_message_list'),
    path('chat/threads/<uuid:thread_id>/attachments/', chat_views.MessageAttachmentUploadView.as_view(), name='chat_attachment_upload'),
    path('chat/threads/<uuid:thread_id>/share/', chat_views.ShareObjectView.as_view(), name='chat_share_object'),
    path('chat/messages/<uuid:message_id>/react/', chat_views.MessageReactionView.as_view(), name='chat_message_react'),
    path('chat/calls/', chat_views.CallLogView.as_view(), name='chat_call_start'),
    path('chat/calls/<uuid:id>/status/', chat_views.CallStatusUpdateView.as_view(), name='chat_call_status'),
    path('chat/relationships/', chat_views.MyRelationshipsView.as_view(), name='chat_relationships'),
    path('announcements/', chat_views.AnnouncementView.as_view(), name='announcement'),

    # Legacy aliases kept for existing frontend clients.
    path('messages/', chat_views.MessageThreadListView.as_view(), name='message_threads'),
    path('messages/<uuid:thread_id>/', chat_views.MessageListView.as_view(), name='message_detail'),
]

# WhatsApp bot
from .whatsapp_bot import WhatsAppWebhookView
urlpatterns += [
    path('whatsapp/webhook/', WhatsAppWebhookView.as_view(), name='whatsapp_webhook'),
]
