from django.urls import include, path


urlpatterns = [
    path(
        "api/acceso/",
        include("acceso.urls"),
    ),
    path(
        "api/profesionales/",
        include("profesionales.urls"),
    ),
    path(
        "api/marketplace/",
        include("marketplace.urls"),
    ),
    path(
        "api/solicitudes/",
        include("solicitudes.urls"),
    ),
    path("api/reagendamientos/", include("reagendamientos.urls")),
    path(
        "api/coordinacion/",
        include("coordinacion.urls"),
    ),
    path(
        "api/pagos/",
        include("pagos.urls"),
    ),
    path(
        "api/seguimiento/",
        include("seguimiento.urls"),
    ),
    path(
        "api/retroalimentacion/",
        include("retroalimentacion.urls"),
    ),
    path(
        "api/backoffice/",
        include("backoffice.urls"),
    ),
]