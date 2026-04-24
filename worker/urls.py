from django.urls import path
from . import views

app_name = 'worker'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('ads/', views.my_ads, name='my_ads'),
    path('ads/create/', views.create_ad, name='create_ad'),
    path('ads/edit/<int:pk>/', views.edit_ad, name='edit_ad'),
    path('ads/delete/<int:pk>/', views.delete_ad, name='delete_ad'),
    path('orders/', views.orders, name='orders'),
    path('orders/<int:pk>/accept/', views.accept_order, name='accept_order'),
    path('orders/<int:pk>/reject/', views.reject_order, name='reject_order'),
    path('orders/<int:pk>/complete/', views.complete_order, name='complete_order'),
    path('orders/history/', views.order_history, name='order_history'),
    path('bonuses/', views.bonuses, name='bonuses'),
    path('bonuses/<int:pk>/claim/', views.claim_bonus, name='claim_bonus'),
    path('profile/', views.profile, name='profile'),
]
