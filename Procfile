web: python manage.py migrate && python manage.py shell -c "
from django.contrib.sites.models import Site
Site.objects.update_or_create(id=1, defaults={'domain':'otta-moyka.onrender.com','name':'OTTA'})
from allauth.socialaccount.models import SocialApp
import os
app, _ = SocialApp.objects.get_or_create(provider='google', name='Google')
app.client_id = os.environ.get('GOOGLE_CLIENT_ID','')
app.secret = os.environ.get('GOOGLE_CLIENT_SECRET','')
app.save()
app.sites.add(1)
print('OK')
" && python manage.py collectstatic --noinput && daphne automoyka.asgi:application --port $PORT --bind 0.0.0.0