
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsProfesional
from profesionales.models import Profesional
from profesionales.serializers import PerfilProfesionalSerializer


class CrearMiPerfilProfesionalView(APIView):
    authentication_classes = [SesionSkillyAuthentication]
    permission_classes = [EsProfesional]
    http_method_names = ["post", "options"]

    def post(self, request):
        if getattr(request.user, "rol", None) != "PROFESIONAL":
            return Response(
                {"mensaje": "Solo los profesionales pueden crear su perfil."},
                status=status.HTTP_403_FORBIDDEN,
            )

        entrada = PerfilProfesionalSerializer(data=request.data)

        if not entrada.is_valid():
            return Response(
                entrada.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        datos = dict(entrada.validated_data)

        nombres = str(datos.get("nombres") or "").strip()
        apellidos = str(datos.get("apellidos") or "").strip()

        if not nombres or not apellidos:
            return Response(
                {
                    "mensaje": (
                        "Los nombres y apellidos son obligatorios."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            usuario = (
                type(request.user).objects
                .select_for_update()
                .get(pk=request.user.pk)
            )

            if Profesional.objects.filter(id_usuario=usuario).exists():
                return Response(
                    {
                        "mensaje": (
                            "Ya existe un perfil profesional. "
                            "Utiliza la opcion de actualizar perfil."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            profesional = Profesional.objects.create(
                id_usuario=usuario,
                nombres=nombres,
                apellidos=apellidos,
                telefono=datos.get("telefono") or None,
                titulo_profesional=(
                    datos.get("titulo_profesional") or None
                ),
                resumen=datos.get("resumen") or None,
                ubicacion=datos.get("ubicacion") or None,
                estado_validacion="PENDIENTE",
                fecha_registro=timezone.now(),
            )

        salida = PerfilProfesionalSerializer(profesional)

        return Response(
            {
                "mensaje": "Perfil profesional creado correctamente.",
                "perfil": salida.data,
            },
            status=status.HTTP_201_CREATED,
        )
