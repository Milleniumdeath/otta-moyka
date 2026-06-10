from django.urls import path
from . import views
from . import reports as reports_views
from finance import views as finance_views
from finance import forecast as finance_forecast

app_name = 'owner'

urlpatterns = [
    path('dashboard/',              views.dashboard,        name='dashboard'),
    path('orders/history/',         views.order_history,    name='order_history'),
    path('receipts/<int:pk>/',      views.receipt_detail,   name='receipt_detail'),

    # Laboratoriya — AI kimyoviy formulalar
    path('lab/',                    views.lab_dashboard,    name='lab_dashboard'),
    path('lab/save/',               views.lab_save,         name='lab_save'),
    path('lab/<int:pk>/',           views.lab_detail,       name='lab_detail'),
    path('lab/<int:pk>/delete/',    views.lab_delete,       name='lab_delete'),
    path('lab/<int:pk>/fav/',       views.lab_favorite,     name='lab_favorite'),
    path('workers/',                views.workers,          name='workers'),
    path('workers/approve/<int:pk>/', views.approve_worker, name='approve_worker'),
    path('workers/delete/<int:pk>/',  views.delete_worker,  name='delete_worker'),
    path('customers/',              views.customers,        name='customers'),
    path('customers/delete/<int:pk>/', views.delete_customer, name='delete_customer'),
    path('bonuses/',                views.bonuses,          name='bonuses'),
    path('bonuses/create/',         views.create_bonus,     name='create_bonus'),
    path('bonuses/edit/<int:pk>/',  views.edit_bonus,       name='edit_bonus'),
    path('bonuses/delete/<int:pk>/',views.delete_bonus,     name='delete_bonus'),
    path('cameras/',                views.cameras,          name='cameras'),
    path('profile/',                views.profile,          name='profile'),

    # Statistika va hisobot
    path('reports/',                reports_views.reports,    name='reports'),
    path('reports/pdf/',            reports_views.report_pdf, name='report_pdf'),
    path('pricelist/', views.pricelist_view, name='pricelist'),
    path('pricelist/create/', views.pricelist_create, name='pricelist_create'),
    path('pricelist/<int:pk>/delete/', views.pricelist_delete, name='pricelist_delete'),

    # Kirim & Chiqim
    path('finance/',                        finance_views.finance,        name='finance'),
    path('finance/forecast/',               finance_forecast.forecast,    name='finance_forecast'),
    path('finance/expense/add/',            finance_views.add_expense,    name='add_expense'),
    path('finance/income/add/',             finance_views.add_income,     name='add_income'),
    path('finance/expense/delete/<int:pk>/',finance_views.delete_expense, name='delete_expense'),
    path('finance/income/delete/<int:pk>/', finance_views.delete_income,  name='delete_income'),
]