from django.conf.urls import url, include
from django.conf import settings
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'changes', views.ChangeGetViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browseable API.
urlpatterns = [
    url(r'^api/v1/', include(router.urls)),
    url(r'^api/v1/change/', views.ChangePost.as_view()),
    url(r'^api/v1/optout/', views.receive_identity_store_optout,
        name="identity_store_optout"),
]
