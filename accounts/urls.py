from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/',         views.register,          name='register'),
    path('login/',            views.user_login,        name='login'),
    path('logout/',           views.user_logout,       name='logout'),
    path('verify-email/',     views.verify_email,      name='verify_email'),
    path('resend-code/',      views.resend_code,       name='resend_code'),
    path('worker-register/',  views.worker_register,   name='worker_register'),
    path('pending-approval/', views.pending_approval,  name='pending_approval'),
    path('redirect/',         views.role_redirect,     name='role_redirect'),
]
