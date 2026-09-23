"""
URL configuration for BusinessManager project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import path, include

from BusinessManager import settings

urlpatterns = [
    path('', include('app.core.urls')),
    path('dokument/', include('app.dokument.urls')),
    path('faktura/', include('app.faktura.urls')),
    path('gwarancja/', include('app.gwarancja.urls')),
    path('kalendarz/', include('app.kalendarz.urls')),
    path('klient/', include('app.klient.urls')),
    path('magazyn/', include('app.magazyn.urls')),
    path('oferta_praca/', include('app.oferta_praca.urls')),
    path('pojazd/', include('app.pojazd.urls')),
    path('protokol/', include('app.protokol.urls')),
    path('rcp/', include('app.rcp.urls')),
    path('serwis/', include('app.serwis.urls')),
    path('urlop/', include('app.urlop.urls')),
    path('urzadzenie/', include('app.urzadzenie.urls')),
    path('uzytkownik/', include('app.uzytkownik.urls')),
    path('zadanie/', include('app.zadanie.urls')), 
    path('praca/', include('app.praca.urls')),
    path('sprzet/', include('app.sprzet.urls')),
    path('obsluga/', include('app.obsluga.urls')),
    path('wsparcie/', include('app.wsparcie.urls')),
    path('admin/', admin.site.urls),
    path("accounts/", include("allauth.urls")),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Własne strony błędów panelu (aktywne przy DEBUG=False).
handler404 = "app.core.views.error_views.error_404"
handler403 = "app.core.views.error_views.error_403"

print("WEBSITE URLS loaded...\n\n")
