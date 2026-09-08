from django.urls import include, path

urlpatterns = [
    path("referral/", include("solutions.urls_referral")),
    path("security/", include("solutions.urls_security")),
    path("uniform/", include("solutions.urls_uniform")),
    path("hr/", include("solutions.urls_hr")),
    path("automation/", include("solutions.urls_automation")),
    path("support/", include("solutions.urls_support")),
    path("appearance/", include("solutions.urls_appearance")),
]
