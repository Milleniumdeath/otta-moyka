from django.urls import path
from . import views

app_name = 'customer'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('cars/', views.my_cars, name='my_cars'),
    path('cars/add/', views.add_car, name='add_car'),
    path('cars/edit/<int:pk>/', views.edit_car, name='edit_car'),
    path('cars/delete/<int:pk>/', views.delete_car, name='delete_car'),
    path('orders/', views.orders, name='orders'),
    path('orders/<int:ad_pk>/book/', views.book_order, name='book_order'),
    path('orders/<int:pk>/review/', views.add_review, name='add_review'),
    path('orders/history/', views.order_history, name='order_history'),
    path('receipts/', views.receipts_list, name='receipts_list'),
    path('receipts/<int:pk>/', views.receipt_detail, name='receipt_detail'),
    path('reminders/', views.reminders_list, name='reminders_list'),
    path('reminders/<int:pk>/cancel/', views.reminder_cancel, name='reminder_cancel'),
    path('bonuses/', views.bonuses, name='bonuses'),
    path('bonuses/<int:pk>/claim/', views.claim_bonus, name='claim_bonus'),
    path('profile/', views.profile, name='profile'),
]
