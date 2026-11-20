"""Entregas documentales opcionales POR SERVICIO, no por profesion.

Ningun archivo se almacena en MEDIA_ROOT, ni en una URL publica.
La aceptacion de una entrega y el pago conservan sus rutas y reglas originales.
"""
from __future__ import annotations
import uuid
import re
import unicodedata
import zipfile
from pathlib import Path
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from django.http import FileResponse, Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from rest_framework import status, serializers
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from acceso.authentication import SesionSkillyAuthentication
from acceso.permissions import EsProfesional, EsAdministracionSkilly
from backoffice.services import registrar_evento_trazabilidad
from coordinacion.models import PrestacionServicio
from profesionales.models import Profesional
from solicitudes.referencias import leer_referencia_seguimiento
from .models import Entrega
from .serializers import EntregaSerializer, RegistrarEntregaSerializer
from django.db.models import Max

MAX_ARCHIVOS=3
MAX_BYTES=10*1024*1024
MAX_TOTAL=25*1024*1024
EXTENSIONES={'.pdf':'application/pdf','.jpg':'image/jpeg','.jpeg':'image/jpeg','.png':'image/png',
             '.docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
             '.xlsx':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
             '.pptx':'application/vnd.openxmlformats-officedocument.presentationml.presentation',
             '.zip':'application/zip'}
RAIZ_PRIVADA=Path(settings.BASE_DIR)/'entregas_privadas_e3'

class ArchivoEntregaE3(models.Model):
    """Registra metadatos de un archivo de entrega almacenado fuera del área pública."""

    id_archivo=models.BigAutoField(primary_key=True)
    id_entrega=models.ForeignKey(Entrega,models.DO_NOTHING,db_column='id_entrega')
    nombre_original=models.CharField(max_length=255)
    ruta_privada=models.CharField(max_length=255,unique=True)
    tipo_mime=models.CharField(max_length=120)
    tamanio_bytes=models.BigIntegerField()
    fecha_subida=models.DateTimeField()
    class Meta:
        """Vincula el modelo con la tabla SQL preexistente `archivo_entrega_e3`."""

        managed=False
        db_table='archivo_entrega_e3'

# Las opciones se derivan del servicio publicado. Nadie debe habilitarlas
# manualmente en administracion. El cliente nunca decide que formato admite el servidor.
FORMATOS_DOCUMENTALES=('.pdf','.jpg','.jpeg','.png','.docx','.xlsx','.pptx')
FORMATOS_TECNICOS=tuple(EXTENSIONES)
SIN_ARCHIVOS=()

def _normalizar(texto):
    """Normaliza texto para clasificar servicios sin depender de tildes o mayúsculas."""

    texto=unicodedata.normalize('NFKD',str(texto or '').casefold())
    return ''.join(c for c in texto if not unicodedata.combining(c))

def politica_entrega_servicio(servicio):
    """Clasifica el servicio por categoría, nombre y alcance para orientar sus adjuntos.

    La regla no obliga a subir archivos: descripción y referencia siguen siendo
    válidas en el flujo sin adjuntos. La coincidencia técnica tiene prioridad
    sobre la clasificación de sesiones descriptivas.

    Args:
        servicio: Servicio con nombre, descripción, alcance y categoría opcionales.

    Returns:
        dict: Tipo TECNICO, DESCRIPTIVO o DOCUMENTAL, permiso de adjuntos,
        formatos y orientación. Usa texto sin tildes ni distinción de mayúsculas.
    """
    categoria=_normalizar(getattr(getattr(servicio,'id_categoria',None),'nombre',''))
    nombre=_normalizar(getattr(servicio,'nombre',''))
    alcance=' '.join((_normalizar(getattr(servicio,'descripcion','')),
                     _normalizar(getattr(servicio,'alcance',''))))
    conjunto=' '.join((categoria,nombre,alcance))
    patrones_tecnicos=(r'\bweb\b',r'\bsoftware\b',r'\bprogramacion\b',
        r'\baplicacion(?:es)?\b',r'\bapps?\b',r'\bfrontend\b',r'\bbackend\b',
        r'\bapi\b',r'\bcodigo fuente\b',r'\bbases? de datos\b',
        r'\binformatica\b',r'\btecnolog(?:ia|ico|icos)\b',r'\bsistemas? informaticos?\b')
    if any(re.search(x,conjunto) for x in patrones_tecnicos):
        return {'tipo':'TECNICO','permitir_archivos':True,
                'formatos_permitidos':list(FORMATOS_TECNICOS),
                'orientacion':'Puedes adjuntar documentos o un ZIP de tu entrega tecnica. No es obligatorio.'}
    # Sesiones que expresamente no incluyen documentos: solo constancia descriptiva.
    sesiones=(r'\bmentoria\b',r'\bentrevista\b',r'\bcharla\b',
             r'\bsesion(?:es)?\b',r'\breunion\b',r'\bcoaching\b',
             r'\borientacion verbal\b',r'\bconsulta verbal\b')
    artefactos=(r'\binforme\b',r'\bentregable\b',r'\bdocument(?:o|acion)\b',
               r'\bmaterial\b',r'\bplantilla\b',r'\bplanilla\b',
               r'\bpresentacion\b',r'\breporte\b',r'\bmanual\b')
    if any(re.search(x,nombre) for x in sesiones) and not any(re.search(x,alcance) for x in artefactos):
        return {'tipo':'DESCRIPTIVO','permitir_archivos':False,
                'formatos_permitidos':[],
                'orientacion':'Registra la actividad mediante descripcion y referencia, sin adjuntos.'}
    # Categoria corporativa o casos ambiguos: respaldos documentales optativos,
    # nunca se exige codigo ni se fuerza una carga.
    return {'tipo':'DOCUMENTAL','permitir_archivos':True,
            'formatos_permitidos':list(FORMATOS_DOCUMENTALES),
            'orientacion':'Si el servicio genero informes o documentos, puedes adjuntarlos de forma opcional.'}

def servicio_de_prestacion(prestacion):
    """Devuelve el servicio de catálogo vinculado a la solicitud de prestacion.

    Args:
        prestacion (PrestacionServicio): Prestación con su solicitud relacionada.

    Returns:
        Servicio: Servicio asociado, sin comprobar aquí su estado de publicación.
    """

    return prestacion.id_solicitud.id_servicio

def archivos_de_prestacion(prestacion):
    """Lista metadatos de archivos asociados a las entregas de una prestación.

    Args:
        prestacion (PrestacionServicio): Prestación ya autorizada por la vista.

    Returns:
        list[dict]: Identificadores de archivo y entrega, nombre, tamaño y fecha,
        ordenados por entrega y archivo. No expone rutas privadas ni URLs.
    """

    qs=ArchivoEntregaE3.objects.filter(id_entrega__id_prestacion=prestacion).order_by('id_entrega_id','id_archivo')
    return [dict(id_archivo=x.id_archivo,id_entrega=x.id_entrega_id,nombre=x.nombre_original,
                 tamano=x.tamanio_bytes,fecha=x.fecha_subida) for x in qs]

def validar_archivo(archivo,formatos_permitidos=None):
    """Valida nombre, extensión, tamaño y firma antes del almacenamiento privado.

    Para documentos Office y ZIP examina el índice sin extraer sus archivos:
    limita entradas, tamaños declarados y relaciones de compresión, y rechaza
    ciertos nombres de rutas y ejecutables. No inspecciona íntegramente cada
    contenido ni garantiza que el archivo esté libre de código malicioso.

    Args:
        archivo: Archivo cargado con name, size, read y seek; cursor inicial en cero.
        formatos_permitidos (Iterable[str] | None): Extensiones de la política
            del servicio; None permite cualquiera de EXTENSIONES.

    Returns:
        tuple[str, str, str]: Nombre sin directorios, extensión y MIME asignado
        por el servidor. Restablece el cursor tras la inspección.

    Raises:
        ValueError: Si el nombre, formato, tamaño, firma o índice no cumplen
            las restricciones. El límite individual es de 10 MiB.
    """

    nombre=str(archivo.name).replace('\\','/').split('/')[-1].strip()
    if not nombre or len(nombre)>180 or any(ord(c)<32 for c in nombre):
        raise ValueError('Nombre de archivo invalido.')
    extension=Path(nombre).suffix.lower()
    permitidos = set(EXTENSIONES) if formatos_permitidos is None else set(formatos_permitidos)
    if extension not in EXTENSIONES or extension not in permitidos:
        raise ValueError('Formato no permitido para este servicio.')
    if not 0 < archivo.size <= MAX_BYTES:
        raise ValueError('Cada archivo debe tener entre 1 byte y 10 MB.')
    cabecera=archivo.read(16)
    archivo.seek(0)
    if extension=='.pdf' and not cabecera.startswith(b'%PDF-'):
        raise ValueError('La firma del PDF no es valida.')
    if extension in ('.jpg','.jpeg') and not cabecera.startswith(bytes.fromhex('FFD8FF')):
        raise ValueError('La firma de la imagen JPG no es valida.')
    if extension=='.png' and not cabecera.startswith(bytes.fromhex('89504E470D0A1A0A')):
        raise ValueError('La firma de la imagen PNG no es valida.')
    if extension in ('.docx','.xlsx','.pptx','.zip'):
        if not zipfile.is_zipfile(archivo):
            archivo.seek(0)
            raise ValueError('El documento comprimido no es valido.')
        try:
            with zipfile.ZipFile(archivo) as z:
                info=z.infolist()
                if len(info)>1500 or sum(x.file_size for x in info)>100*1024*1024:
                    raise ValueError('El archivo comprimido excede los limites de seguridad.')
                if any(x.file_size>50*1024*1024 or (x.compress_size and x.file_size>x.compress_size*500)
                       or x.filename.startswith('/') or '..' in Path(x.filename).parts for x in info):
                    raise ValueError('El contenido del archivo comprimido no es seguro.')
                nombres=set(z.namelist())
                requeridos={'.docx':'word/document.xml','.xlsx':'xl/workbook.xml','.pptx':'ppt/presentation.xml'}
                if extension!='.zip' and ('[Content_Types].xml' not in nombres or requeridos[extension] not in nombres):
                    raise ValueError('El tipo de documento no coincide con el archivo.')
                if any(n.lower().endswith(('vbaproject.bin','.exe','.dll','.bat','.cmd')) for n in nombres):
                    raise ValueError('El archivo comprimido contiene elementos no permitidos.')
        except (zipfile.BadZipFile, OSError) as exc:
            raise ValueError('No es posible revisar el archivo comprimido.') from exc
        finally:
            archivo.seek(0)
    return nombre, extension, EXTENSIONES[extension]

def almacenamiento():
    """Construye un almacén de archivos en RAIZ_PRIVADA.

    Returns:
        FileSystemStorage: Almacén utilizado directamente por las vistas de
        descarga autorizadas; estas no necesitan publicar una URL del archivo.
    """

    return FileSystemStorage(location=str(RAIZ_PRIVADA),base_url=None)

def abrir_privado(archivo):
    """Abre un adjunto después de comprobar su referencia local y existencia.

    Args:
        archivo (ArchivoEntregaE3): Registro cuyo acceso ya autorizó la vista.

    Returns:
        FileResponse: Adjunto application/octet-stream con nombre original y
        cabeceras de privacidad; esta función no comprueba identidad ni permisos.

    Raises:
        Http404: Si la referencia está vacía, contiene directorios o no existe
            en el almacenamiento.
        OSError: Si falla la apertura del archivo.
    """

    ruta=archivo.ruta_privada
    if not ruta or '/' in ruta or '\\' in ruta or Path(ruta).name!=ruta:
        raise Http404()
    store=almacenamiento()
    if not store.exists(ruta):
        raise Http404()
    respuesta=FileResponse(store.open(ruta,'rb'),as_attachment=True,
                           filename=archivo.nombre_original,content_type='application/octet-stream')
    respuesta['Cache-Control']='private, no-store'
    respuesta['X-Content-Type-Options']='nosniff'
    respuesta['Referrer-Policy']='no-referrer'
    return respuesta

class EntregablesProfesionalE3View(APIView):
    """Lista política y archivos de entregas propias del profesional."""

    authentication_classes=[SesionSkillyAuthentication]
    permission_classes=[EsProfesional]
    def get(self,request,id_prestacion):
        """Lista política y metadatos de adjuntos de una prestación propia.

        Args:
            request: Petición del profesional autenticado.
            id_prestacion (int): Prestación consultada.

        Returns:
            Response: 200 con política, archivos y límites individuales, o 404 si
            falta el perfil o la prestación no le pertenece. No devuelve los bytes.
        """
        profesional=Profesional.objects.filter(id_usuario=request.user).first()
        prestacion=PrestacionServicio.objects.select_related('id_solicitud').filter(
            id_prestacion=id_prestacion,id_profesional=profesional).first() if profesional else None
        if not prestacion:
            return Response({'mensaje':'Prestacion no encontrada.'},status=404)
        politica=politica_entrega_servicio(servicio_de_prestacion(prestacion))
        return Response({**politica,'archivos':archivos_de_prestacion(prestacion),
                         'max_archivos':MAX_ARCHIVOS,'max_bytes':MAX_BYTES})

@method_decorator(csrf_protect,name='dispatch')
class RegistrarEntregaConArchivosE3View(APIView):
    """Registra entrega y adjuntos privados de forma transaccional."""

    authentication_classes=[SesionSkillyAuthentication]
    permission_classes=[EsProfesional]
    parser_classes=[MultiPartParser,FormParser]
    def post(self,request,id_prestacion):
        """Registra una entrega con entre uno y tres adjuntos privados.

        Args:
            request: Petición multipart con descripcion, referencia_entrega opcional
                y archivos, hasta 25 MiB en conjunto y 10 MiB por archivo.
            id_prestacion (int): Prestación propia en CONTRATADA, EN_EJECUCION o
                EN_PROGRESO cuya política permite adjuntos.

        Returns:
            Response: 201 con la entrega, 400 por datos o archivos inválidos, 403
            por falta de perfil o política sin adjuntos, 404 por prestación ajena o
            inexistente y 409 por estado incompatible. Asigna la siguiente versión
            bajo bloqueo y guarda metadatos y trazabilidad en la transacción.

        Si una excepción ocurre después de guardar archivos, intenta eliminar las
        rutas nuevas antes de propagarla. La transacción revierte los registros de
        base de datos; los archivos dependen de esa limpieza compensatoria.
        """
        profesional=Profesional.objects.filter(id_usuario=request.user).first()
        if not profesional:
            return Response({'mensaje':'Perfil profesional no disponible.'},status=403)
        entrada=RegistrarEntregaSerializer(data=request.data)
        if not entrada.is_valid():
            return Response(entrada.errors,status=400)
        archivos=request.FILES.getlist('archivos')
        if not (1<=len(archivos)<=MAX_ARCHIVOS) or sum(a.size for a in archivos)>MAX_TOTAL:
            return Response({'mensaje':'Adjunta de 1 a 3 archivos, maximo 25 MB en total.'},status=400)
        guardados=[]
        try:
            with transaction.atomic():
                prestacion=PrestacionServicio.objects.select_for_update().select_related('id_solicitud').filter(
                    id_prestacion=id_prestacion,id_profesional=profesional).first()
                if not prestacion:
                    return Response({'mensaje':'Prestacion no encontrada.'},status=404)
                if prestacion.estado not in ('CONTRATADA','EN_EJECUCION','EN_PROGRESO'):
                    return Response({'mensaje':'La prestacion no admite nuevas entregas.'},status=409)
                politica=politica_entrega_servicio(servicio_de_prestacion(prestacion))
                if not politica['permitir_archivos']:
                    return Response({'mensaje':'Este servicio se registra con descripcion y referencia, sin adjuntos.'},status=403)
                try:
                    comprobados=[validar_archivo(a,politica['formatos_permitidos']) for a in archivos]
                except ValueError as exc:
                    return Response({'mensaje':str(exc)},status=400)
                version=(Entrega.objects.filter(id_prestacion=prestacion).aggregate(Max('version'))['version__max'] or 0)+1
                entrega=Entrega.objects.create(id_prestacion=prestacion,version=version,
                    descripcion=entrada.validated_data['descripcion'],
                    referencia_entrega=entrada.validated_data.get('referencia_entrega') or None,
                    fecha_entrega=timezone.now(),estado='ENTREGADA')
                store=almacenamiento()
                for archivo,(nombre,ext,mime) in zip(archivos,comprobados):
                    ruta=store.save(uuid.uuid4().hex+ext,archivo)
                    guardados.append(ruta)
                    ArchivoEntregaE3.objects.create(id_entrega=entrega,nombre_original=nombre,ruta_privada=ruta,
                        tipo_mime=mime,tamanio_bytes=archivo.size,fecha_subida=timezone.now())
                registrar_evento_trazabilidad(usuario=request.user,entidad_tipo='entrega',entidad_id=entrega.id_entrega,
                    accion='REGISTRAR_ENTREGA',detalle_resumido=f'Entrega version {version} con {len(archivos)} respaldo(s) para prestacion {id_prestacion}.'[:255])
        except Exception:
            store=almacenamiento()
            for ruta in guardados:
                try: store.delete(ruta)
                except OSError: pass
            raise
        return Response({'mensaje':'Entrega y adjuntos registrados correctamente.',
                         'entrega':EntregaSerializer(entrega).data},status=201)

class EntregablesEmpresaE3View(APIView):
    """Lista entregables para la empresa mediante su referencia privada."""

    authentication_classes=[]
    permission_classes=[AllowAny]
    def get(self,request,referencia):
        """Lista metadatos de adjuntos mediante la referencia privada empresarial.

        Args:
            request: Petición de consulta sin sesión.
            referencia (str): Referencia firmada con solicitud y contacto.

        Returns:
            Response: 200 con archivos, 400 por referencia inválida o 404 si no
            hay una prestación que corresponda a la solicitud y contacto.
        """
        validada=leer_referencia_seguimiento(referencia)
        if not validada:
            return Response({'mensaje':'Referencia invalida.'},status=400)
        prestacion=PrestacionServicio.objects.filter(id_solicitud_id=validada['id_solicitud'],
            id_solicitud__id_contacto_id=validada['id_contacto']).first()
        if not prestacion:
            return Response({'mensaje':'La solicitud no corresponde a esta referencia.'},status=404)
        return Response({'archivos':archivos_de_prestacion(prestacion)})

@method_decorator(never_cache,name='dispatch')
class DescargaEntregaEmpresaE3View(APIView):
    """Descarga un archivo cuando pertenece a la prestación empresarial referenciada."""

    authentication_classes=[]
    permission_classes=[AllowAny]
    def get(self,request,referencia,id_archivo):
        """Descarga un adjunto solo si pertenece a la solicitud y contacto firmados.

        Args:
            request: Petición sin sesión, autorizada mediante la referencia.
            referencia (str): Referencia privada firmada de seguimiento.
            id_archivo (int): Archivo solicitado.

        Returns:
            FileResponse: Adjunto privado sin caché.

        Raises:
            Http404: Si la referencia es inválida, el archivo no pertenece a la
                prestación autorizada o falta su referencia física.
            OSError: Si falla la apertura del archivo.
        """
        validada=leer_referencia_seguimiento(referencia)
        if not validada:
            raise Http404()
        archivo=ArchivoEntregaE3.objects.select_related('id_entrega').filter(
            id_archivo=id_archivo,id_entrega__id_prestacion__id_solicitud_id=validada['id_solicitud'],
            id_entrega__id_prestacion__id_solicitud__id_contacto_id=validada['id_contacto']).first()
        if not archivo:
            raise Http404()
        return abrir_privado(archivo)

@method_decorator(never_cache,name='dispatch')
class DescargaEntregaProfesionalE3View(APIView):
    """Descarga un archivo que pertenece al profesional autenticado."""

    authentication_classes=[SesionSkillyAuthentication]
    permission_classes=[EsProfesional]
    def get(self,request,id_archivo):
        """Descarga un adjunto solo para el profesional propietario de la prestación.

        Args:
            request: Petición del profesional autenticado.
            id_archivo (int): Identificador del adjunto solicitado.

        Returns:
            FileResponse: Adjunto privado sin caché.

        Raises:
            Http404: Si falta perfil, el archivo es ajeno/inexistente o la referencia
                física no es válida.
            OSError: Si falla la apertura del archivo.
        """
        profesional=Profesional.objects.filter(id_usuario=request.user).first()
        archivo=ArchivoEntregaE3.objects.filter(id_archivo=id_archivo,
            id_entrega__id_prestacion__id_profesional=profesional).first() if profesional else None
        if not archivo:
            raise Http404()
        return abrir_privado(archivo)

@method_decorator(never_cache,name='dispatch')
class DescargaEntregaAdminE3View(APIView):
    """Permite descargar adjuntos privados a usuarios con permiso administrativo."""

    authentication_classes=[SesionSkillyAuthentication]
    permission_classes=[EsAdministracionSkilly]
    def get(self,request,id_archivo):
        """Descarga un adjunto privado para una sesión administrativa autorizada.

        Args:
            request: Petición con permiso EsAdministracionSkilly; no exige que el
                usuario sea el responsable asignado de la prestación.
            id_archivo (int): Archivo que se descargará.

        Returns:
            FileResponse: Adjunto sin caché.

        Raises:
            Http404: Si no existe el registro o su referencia física no es válida.
            OSError: Si falla la apertura del archivo.
        """
        archivo=ArchivoEntregaE3.objects.filter(id_archivo=id_archivo).first()
        if not archivo:
            raise Http404()
        return abrir_privado(archivo)
