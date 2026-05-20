"""PWA endpoints: web app manifest, service worker, offline page.

Served from the site root so the service worker controls the whole origin
(a SW served from /static/ would only get /static/ scope).
"""
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control

APP_NAME = "OTTA Moyka"
THEME_COLOR = "#050a0f"
BACKGROUND_COLOR = "#050a0f"


@cache_control(max_age=86400)
def manifest(request):
    data = {
        "name": "OTTA — Avto Moyka",
        "short_name": APP_NAME,
        "description": "Oltiariq Tol Tagi Avto Moyka — onlayn buyurtma va bonus tizimi",
        "lang": "uz",
        "dir": "ltr",
        "start_url": "/?source=pwa",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": BACKGROUND_COLOR,
        "theme_color": THEME_COLOR,
        "categories": ["business", "lifestyle", "utilities"],
        "icons": [
            {
                "src": static("pwa/icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": static("pwa/icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": static("pwa/icon-512-maskable.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
        "shortcuts": [
            {
                "name": "Buyurtma berish",
                "url": "/customer/orders/create/?source=pwa",
            },
            {
                "name": "Bonuslarim",
                "url": "/customer/bonuses/?source=pwa",
            },
        ],
    }
    return JsonResponse(data, content_type="application/manifest+json")


@cache_control(no_cache=True)
def service_worker(request):
    body = render(
        request,
        "pwa/sw.js",
        {
            "offline_url": "/offline/",
            "precache": [
                "/offline/",
                static("pwa/icon-192.png"),
                static("pwa/icon-512.png"),
            ],
        },
    ).content
    resp = HttpResponse(body, content_type="application/javascript")
    # allow root scope even though Django routes this URL itself
    resp["Service-Worker-Allowed"] = "/"
    return resp


def offline(request):
    return render(request, "pwa/offline.html")
