import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# -------------------------------------------------------------
# PRESENTATION CONFIGURATION & DESIGN SYSTEM
# -------------------------------------------------------------
prs = Presentation()
prs.slide_width = Inches(13.333)  # 16:9 Widescreen
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# Professional Corporate Palette (Executive Navy & Industrial Slate)
COLOR_NAVY_DARK   = RGBColor(20, 35, 60)      # #14233C - Deep Executive Navy
COLOR_NAVY_MID    = RGBColor(27, 42, 74)      # #1B2A4A - Core Header Navy
COLOR_BLUE_ACCENT = RGBColor(13, 110, 253)    # #0D6EFD - Primary Accent Blue
COLOR_SLATE_GRAY  = RGBColor(80, 90, 105)     # #505A69 - Subtitle Slate Gray
COLOR_CARD_BG     = RGBColor(248, 250, 253)   # #F8FAFD - Card Background
COLOR_CARD_BORDER = RGBColor(220, 226, 236)   # #DCE2EC - Subtle Border
COLOR_TEXT_MAIN   = RGBColor(30, 35, 45)      # #1E232D - High Contrast Charcoal
COLOR_TEXT_MUTED  = RGBColor(100, 110, 125)   # #646E7D - Muted Body
COLOR_WHITE       = RGBColor(255, 255, 255)   # #FFFFFF
COLOR_PILL_BG     = RGBColor(230, 240, 255)   # #E6F0FF - Pill background
COLOR_PILL_TEXT   = RGBColor(11, 83, 185)     # #0B53B9 - Pill text

SCREENSHOT_DIR = os.path.join(os.getcwd(), 'output', 'screenshots')

def add_header(slide, category, title, subtitle):
    """Draws a standardized corporate header with category pill, title, and subtitle."""
    # Category Pill
    pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.4), Inches(3.2), Inches(0.32))
    pill.fill.solid()
    pill.fill.fore_color.rgb = COLOR_PILL_BG
    pill.line.color.rgb = COLOR_BLUE_ACCENT
    pill.line.width = Pt(1)
    tf_pill = pill.text_frame
    tf_pill.word_wrap = True
    p_pill = tf_pill.paragraphs[0]
    p_pill.text = category.upper()
    p_pill.font.name = 'Arial'
    p_pill.font.size = Pt(9.5)
    p_pill.font.bold = True
    p_pill.font.color.rgb = COLOR_PILL_TEXT
    p_pill.alignment = PP_ALIGN.CENTER

    # Title & Subtitle Box
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.78), Inches(11.7), Inches(0.95))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_title = tf.paragraphs[0]
    p_title.text = title
    p_title.font.name = 'Arial'
    p_title.font.size = Pt(20)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_NAVY_DARK

    p_sub = tf.add_paragraph()
    p_sub.text = subtitle
    p_sub.font.name = 'Calibri'
    p_sub.font.size = Pt(11.5)
    p_sub.font.color.rgb = COLOR_SLATE_GRAY
    p_sub.space_before = Pt(3)

    # Subtle horizontal line
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.8), Inches(11.733), Inches(0.02))
    line.fill.solid()
    line.fill.fore_color.rgb = COLOR_CARD_BORDER
    line.line.fill.background()

def add_footer(slide, current_slide, total_slides=24):
    """Draws a subtle bottom footer with classification and page number."""
    tb = slide.shapes.add_textbox(Inches(0.8), Inches(7.15), Inches(9.0), Inches(0.25))
    tf = tb.text_frame
    tf.word_wrap = False
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.text = "ILSAN Electronics | Sistema de Ejecucion de Manufactura (MES) | Documentacion de Operacion"
    p.font.name = 'Calibri'
    p.font.size = Pt(9)
    p.font.color.rgb = COLOR_TEXT_MUTED

    tb_num = slide.shapes.add_textbox(Inches(11.5), Inches(7.15), Inches(1.0), Inches(0.25))
    tf_num = tb_num.text_frame
    tf_num.word_wrap = False
    tf_num.margin_left = tf_num.margin_top = tf_num.margin_right = tf_num.margin_bottom = 0
    p_num = tf_num.paragraphs[0]
    p_num.text = f"{current_slide} / {total_slides}"
    p_num.alignment = PP_ALIGN.RIGHT
    p_num.font.name = 'Calibri'
    p_num.font.size = Pt(9)
    p_num.font.color.rgb = COLOR_TEXT_MUTED

def add_standard_content_slide(slide_num, category, title, subtitle, cards_data, screenshot_filename, caption_text):
    """
    Standard layout for module slides:
    - Left column (4.8 inches wide): 3 structured informative cards.
    - Right column (6.7 inches wide): High-definition screenshot with container frame & caption.
    """
    slide = prs.slides.add_slide(blank_layout)
    add_header(slide, category, title, subtitle)
    add_footer(slide, slide_num)

    # ----------------- LEFT COLUMN: 3 Structured Cards -----------------
    left_x = Inches(0.8)
    card_width = Inches(4.7)
    card_height = Inches(1.58)
    gap = Inches(0.14)
    start_y = Inches(1.95)

    for i, (card_title, bullet_points) in enumerate(cards_data):
        y_pos = start_y + i * (card_height + gap)
        
        # Card Background Shape
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_x, y_pos, card_width, card_height)
        card.fill.solid()
        card.fill.fore_color.rgb = COLOR_CARD_BG
        card.line.color.rgb = COLOR_CARD_BORDER
        card.line.width = Pt(1)

        # Card Content Textbox
        tb = slide.shapes.add_textbox(left_x + Inches(0.15), y_pos + Inches(0.1), card_width - Inches(0.3), card_height - Inches(0.2))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_ct = tf.paragraphs[0]
        p_ct.text = card_title.upper()
        p_ct.font.name = 'Arial'
        p_ct.font.size = Pt(10)
        p_ct.font.bold = True
        p_ct.font.color.rgb = COLOR_PILL_TEXT

        for bullet in bullet_points:
            p_b = tf.add_paragraph()
            p_b.text = f"- {bullet}"
            p_b.font.name = 'Calibri'
            p_b.font.size = Pt(9.5)
            p_b.font.color.rgb = COLOR_TEXT_MAIN
            p_b.space_before = Pt(2)
            p_b.level = 0

    # ----------------- RIGHT COLUMN: Screenshot Frame -----------------
    right_x = Inches(5.7)
    frame_width = Inches(6.833)
    frame_height = Inches(5.02)
    frame_y = Inches(1.95)

    # Outer frame container
    frame = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, right_x, frame_y, frame_width, frame_height)
    frame.fill.solid()
    frame.fill.fore_color.rgb = RGBColor(240, 243, 248)
    frame.line.color.rgb = COLOR_CARD_BORDER
    frame.line.width = Pt(1.5)

    # Embed Screenshot
    img_path = os.path.join(SCREENSHOT_DIR, screenshot_filename)
    if os.path.exists(img_path):
        img_margin = Inches(0.08)
        img_w = frame_width - (img_margin * 2)
        img_h = frame_height - Inches(0.48)
        slide.shapes.add_picture(img_path, right_x + img_margin, frame_y + img_margin, width=img_w, height=img_h)

    # Screenshot Caption Bar
    caption_box = slide.shapes.add_textbox(right_x + Inches(0.15), frame_y + frame_height - Inches(0.38), frame_width - Inches(0.3), Inches(0.3))
    tf_cap = caption_box.text_frame
    tf_cap.word_wrap = True
    tf_cap.margin_left = tf_cap.margin_top = tf_cap.margin_right = tf_cap.margin_bottom = 0
    p_cap = tf_cap.paragraphs[0]
    p_cap.text = f"Captura del Sistema en Vivo: {caption_text}"
    p_cap.font.name = 'Calibri'
    p_cap.font.size = Pt(8.5)
    p_cap.font.bold = True
    p_cap.font.color.rgb = COLOR_SLATE_GRAY

print("Building presentation deck...")

# =============================================================================
# SLIDE 1: PORTADA EJECUTIVA
# =============================================================================
slide1 = prs.slides.add_slide(blank_layout)

# Dark corporate background for cover
bg = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
bg.fill.solid()
bg.fill.fore_color.rgb = COLOR_NAVY_DARK
bg.line.fill.background()

# Decorative accent bar
bar = slide1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.2), Inches(1.5), Inches(0.15), Inches(4.5))
bar.fill.solid()
bar.fill.fore_color.rgb = COLOR_BLUE_ACCENT
bar.line.fill.background()

# Title Box
tb1 = slide1.shapes.add_textbox(Inches(1.6), Inches(1.5), Inches(10.5), Inches(4.5))
tf1 = tb1.text_frame
tf1.word_wrap = True

p_pill1 = tf1.paragraphs[0]
p_pill1.text = "SISTEMA DE EJECUCION DE MANUFACTURA INDUSTRIAL"
p_pill1.font.name = 'Arial'
p_pill1.font.size = Pt(12)
p_pill1.font.bold = True
p_pill1.font.color.rgb = COLOR_BLUE_ACCENT

p_t1 = tf1.add_paragraph()
p_t1.text = "ILSAN MES: Control, Trazabilidad y Calidad Operativa"
p_t1.font.name = 'Arial'
p_t1.font.size = Pt(32)
p_t1.font.bold = True
p_t1.font.color.rgb = COLOR_WHITE
p_t1.space_before = Pt(12)

p_sub1 = tf1.add_paragraph()
p_sub1.text = "Manual Funcional y Analisis Integral de Interaccion del Usuario en Planta de Ensamble SMT / ASSY"
p_sub1.font.name = 'Calibri'
p_sub1.font.size = Pt(16)
p_sub1.font.color.rgb = RGBColor(190, 205, 225)
p_sub1.space_before = Pt(10)

p_meta1 = tf1.add_paragraph()
p_meta1.text = "Empresa: ILSAN Electronics  |  Version Local: 2026.1  |  Alcance: Modulos Web, Almacen, Produccion y Calidad"
p_meta1.font.name = 'Calibri'
p_meta1.font.size = Pt(12)
p_meta1.font.color.rgb = RGBColor(140, 160, 185)
p_meta1.space_before = Pt(30)

# =============================================================================
# SLIDE 2: MISION, FUNCION Y VALOR ESTRATEGICO DEL MES
# =============================================================================
slide2 = prs.slides.add_slide(blank_layout)
add_header(slide2, "Vision General y Proposito", "Mision y Funcion del Sistema MES en Planta", "Digitalizacion total del flujo productivo para garantizar cero defectos y trazabilidad genealogica")
add_footer(slide2, 2)

# 3 Horizontal Pillar Cards
pillars = [
    ("Trazabilidad Total de Materiales", [
        "Control exhaustivo desde la recepcion de materia prima hasta el embarque final.",
        "Identificacion unitaria de carretes, rollos SMD y componentes mediante codigos de barras unicos.",
        "Genealogia serializada por tarjeta PCB: que lote, proveedor y maquina ensamblo cada circuito.",
        "Historial inmutable de inventarios, retornos y consumos en lineas de montaje."
    ]),
    ("Control de Calidad e Interlock Activo", [
        "Compuertas de calidad obligatorias (Quality Gates) en IQC, LQC y OQC antes de mover producto.",
        "Mecanismo de Interlock: bloqueo automatico de lineas si los herramentales o componentes no coinciden.",
        "Auditoria de Golden Sample (Master Sample) obligatoria al inicio de turno o cambio de modelo.",
        "Monitoreo estadistico continuo de defectos (tableros PPMS) e inspecciones opticas AOI."
    ]),
    ("Planeacion, Eficiencia y Logistica FIFO", [
        "Programacion balanceada de ordenes de trabajo (WO) en lineas SMT, IMT y ensamble ASSY.",
        "Control de desgaste de herramentales criticos: tension de stencils (Metal Mask) y cuchillas de corte.",
        "Almacen de embarques con motor de despacho estricto por First-In, First-Out (FIFO).",
        "Integracion nativa con terminales moviles Zebra PDA (TC15) para escaneo agil en piso."
    ])
]

for idx, (p_title, p_items) in enumerate(pillars):
    c_x = Inches(0.8 + idx * 4.0)
    c_card = slide2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c_x, Inches(2.0), Inches(3.73), Inches(4.9))
    c_card.fill.solid()
    c_card.fill.fore_color.rgb = COLOR_CARD_BG
    c_card.line.color.rgb = COLOR_CARD_BORDER
    c_card.line.width = Pt(1.5)

    c_tb = slide2.shapes.add_textbox(c_x + Inches(0.2), Inches(2.2), Inches(3.33), Inches(4.5))
    c_tf = c_tb.text_frame
    c_tf.word_wrap = True
    c_tf.margin_left = c_tf.margin_top = c_tf.margin_right = c_tf.margin_bottom = 0

    p_h = c_tf.paragraphs[0]
    p_h.text = p_title.upper()
    p_h.font.name = 'Arial'
    p_h.font.size = Pt(11.5)
    p_h.font.bold = True
    p_h.font.color.rgb = COLOR_PILL_TEXT

    for item in p_items:
        p_it = c_tf.add_paragraph()
        p_it.text = f"- {item}"
        p_it.font.name = 'Calibri'
        p_it.font.size = Pt(10)
        p_it.font.color.rgb = COLOR_TEXT_MAIN
        p_it.space_before = Pt(8)

# =============================================================================
# SLIDE 3: ARQUITECTURA TECNOLOGICA Y ECOSISTEMA (UNICA SLIDE DE TECNOLOGIAS)
# =============================================================================
slide3 = prs.slides.add_slide(blank_layout)
add_header(slide3, "Arquitectura del Sistema", "Tecnologias Utilizadas en la Solucion Industrial", "Unica diapositiva tecnica: Componentes de software, base de datos e integracion con hardware")
add_footer(slide3, 3)

tech_blocks = [
    ("Capa de Servidor y Logica", [
        "Python 3.11 / 3.13: Lenguaje nucleo del monolito y micro-modulos.",
        "Flask Framework: Ruteo eficiente, sesiones seguras y arquitectura modular por Blueprints.",
        "Waitress WSGI: Servidor de grado de produccion multihilo optimizado para alta concurrencia.",
        "Logging Idempotente: Registro continuo de eventos de aplicacion sin bloqueo de E/S."
    ]),
    ("Capa de Base de Datos", [
        "MySQL Server 8.0: Motor relacional transaccional de alto rendimiento.",
        "Pool Dinamico de Conexiones: Reutilizacion eficiente de conexiones con reconexion automatica.",
        "Estructura Relacional Normalizada: Mas de 30 tablas para control de lotes, BOM, calidad y usuarios.",
        "Auditoria Inmutable: Registro de mutaciones criticas en la tabla auditoria_sistema."
    ]),
    ("Capa Frontend y UX Industrial", [
        "Arquitectura SPA-Feel: Interfaz fluida basada en HTML5 y llamadas asincronas AJAX.",
        "Vanilla CSS & Bootstrap 5.3: Diseno corporativo adaptativo para estaciones de trabajo y desktop.",
        "Ajax Content Manager: Motor de inyeccion que asegura la carga completa de hojas de estilo.",
        "Seguridad en Cliente: Control de visibilidad y bloqueo de botones segun permisos de usuario."
    ]),
    ("Integracion de Hardware en Planta", [
        "Terminales Zebra PDA TC15: Consumo de APIs REST para recepcion, movimientos y despacho FIFO.",
        "Lectores de Codigo de Barras 1D / 2D QR: Lectura directa de seriales de PCB y cajas OQC.",
        "Impresoras Termicas Zebra (ZPL): Generacion y etiquetado automatico de codigo de almacen.",
        "Equipos de Prueba SMT: Consolidacion de datos de maquinas AOI, probadores ICT y FCT."
    ])
]

for idx, (t_title, t_items) in enumerate(tech_blocks):
    b_x = Inches(0.8 + idx * 3.0)
    b_card = slide3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, b_x, Inches(2.0), Inches(2.78), Inches(4.9))
    b_card.fill.solid()
    b_card.fill.fore_color.rgb = COLOR_CARD_BG
    b_card.line.color.rgb = COLOR_CARD_BORDER
    b_card.line.width = Pt(1.5)

    b_tb = slide3.shapes.add_textbox(b_x + Inches(0.18), Inches(2.2), Inches(2.42), Inches(4.5))
    b_tf = b_tb.text_frame
    b_tf.word_wrap = True
    b_tf.margin_left = b_tf.margin_top = b_tf.margin_right = b_tf.margin_bottom = 0

    b_p_h = b_tf.paragraphs[0]
    b_p_h.text = t_title.upper()
    b_p_h.font.name = 'Arial'
    b_p_h.font.size = Pt(11)
    b_p_h.font.bold = True
    b_p_h.font.color.rgb = COLOR_PILL_TEXT

    for t_item in t_items:
        b_p_it = b_tf.add_paragraph()
        b_p_it.text = f"- {t_item}"
        b_p_it.font.name = 'Calibri'
        b_p_it.font.size = Pt(9.5)
        b_p_it.font.color.rgb = COLOR_TEXT_MAIN
        b_p_it.space_before = Pt(8)

# =============================================================================
# SLIDE 4: ACCESO Y AUTENTICACION DE USUARIOS (/login)
# =============================================================================
add_standard_content_slide(
    slide_num=4,
    category="Seguridad y Control de Acceso",
    title="Autenticacion de Usuarios y Seguridad RBAC",
    subtitle="Portal seguro de inicio de sesion con validacion de credenciales y politicas de planta",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Proteger el acceso a la plataforma MES asegurando que solo personal acreditado opere los modulos.",
            "Validar la identidad del operador contra la base de datos MySQL mediante contrasenas encriptadas.",
            "Establecer la sesion autenticada cifrada (mes_ilsan_session) que define el contexto del usuario."
        ]),
        ("Como Interactua el Usuario", [
            "El operador ingresa a la URL base y visualiza la pantalla institucional de login.",
            "Captura su nombre de usuario asignado y su clave de seguridad personal en los campos designados.",
            "Al presionar 'Iniciar Sesion', el sistema valida las credenciales y lo redirige al Hub corporativo."
        ]),
        ("Validaciones y Reglas de Seguridad", [
            "Validacion de contrasena mediante hashes protegidos con algoritmo seguro.",
            "Control de intentos fallidos para prevenir ataques por fuerza bruta.",
            "Asignacion automatica de roles y permisos departamentales una vez autenticado."
        ])
    ],
    screenshot_filename="01_login.png",
    caption_text="Pantalla de inicio de sesion corporativa (URL: /login)"
)

# =============================================================================
# SLIDE 5: PORTAL CORPORATIVO HUB (/inicio)
# =============================================================================
add_standard_content_slide(
    slide_num=5,
    category="Navegacion Corporativa",
    title="Portal Corporativo Hub de Aplicaciones",
    subtitle="Lanzador centralizado con tarjetas de acceso dinámicas segun el perfil y rol del usuario",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Actuar como la puerta de enlace centralizada a todo el ecosistema de herramientas digitales de la empresa.",
            "Desacoplar los diferentes sistemas: MES de produccion, gestion de defectos, portal IT y calendario.",
            "Brindar una bienvenida personalizada indicando el nombre del usuario y su departamento."
        ]),
        ("Como Interactua el Usuario", [
            "El usuario visualiza un panel con tarjetas interactivas (cards) correspondientes a cada aplicacion.",
            "Al hacer clic en 'ILSAN MES', ingresa directamente a la consola de manufactura y materiales.",
            "Puede acceder a 'Support' para levantar tickets o a 'Calendar' para verificar turnos de produccion."
        ]),
        ("Validaciones y Control de Permisos", [
            "Filtrado dinamico en backend: las tarjetas se muestran u ocultan segun los permisos del rol.",
            "Boton de cierre de sesion seguro ('Logout') que destruye las cookies de sesion activa.",
            "Indicadores visuales de estado para aplicaciones en produccion o en mantenimiento."
        ])
    ],
    screenshot_filename="02_portal_inicio.png",
    caption_text="Lanzador central de aplicaciones corporativas (URL: /inicio)"
)

# =============================================================================
# SLIDE 6: ESPACIO DE TRABAJO PRINCIPAL (/ILSAN-ELECTRONICS)
# =============================================================================
add_standard_content_slide(
    slide_num=6,
    category="Consola de Operacion",
    title="Espacio de Trabajo Principal (ILSAN MES Shell)",
    subtitle="Consola unificada con barra de navegacion superior fija y panel lateral dinamico",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Proveer un espacio de trabajo ergonomico y rapido para operadores, supervisores e ingenieros.",
            "Centralizar los 8 departamentos clave en una barra superior siempre visible.",
            "Permitir la navegacion entre modulos sin recargar la pagina completa mediante arquitectura AJAX."
        ]),
        ("Como Interactua el Usuario", [
            "El usuario hace clic en cualquiera de los 8 botones de navegacion del encabezado principal.",
            "El sistema despliega en el sidebar izquierdo las sub-secciones y formularios correspondientes.",
            "Dispone de un boton 'Sidebar Toggle' para maximizar el area de trabajo en pantallas industriales."
        ]),
        ("Reglas de Negocio y Rendimiento", [
            "El Administrador de Contenido AJAX precarga y valida los estilos CSS antes de renderizar.",
            "Se previene el parpadeo visual y se preservan los filtros de consulta activos.",
            "Boton de 'Log out' fijo en la esquina superior derecha para salida rapida y segura."
        ])
    ],
    screenshot_filename="03_mes_shell.png",
    caption_text="Consola central de manufactura ILSAN MES (URL: /ILSAN-ELECTRONICS)"
)

# =============================================================================
# SLIDE 7: INFORMACION BASICA - MODELOS SMT
# =============================================================================
add_standard_content_slide(
    slide_num=7,
    category="Informacion Basica",
    title="Gestion Maestra de Modelos SMT y Parametros",
    subtitle="Registro y visor centralizado de modelos de ensamble, lados de tarjeta y asignacion de lineas",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Mantener el catalogo maestro de tarjetas electronicas producidas en planta.",
            "Definir para cada modelo los lados de ensamble (TOP / BOT), tiempos de ciclo (CT) y UPH teorico.",
            "Asignar la compatibilidad de cada modelo con las lineas de insercion superficial SMT."
        ]),
        ("Como Interactua el Usuario", [
            "Navega a 'Informacion Basica' -> 'Control de modelos SMT' o 'Visor de Modelos'.",
            "Filtra o busca por codigo de modelo, descripcion o familia de producto.",
            "Visualiza la tabla consolidada con especificaciones tecnicas y lineas autorizadas."
        ]),
        ("Validaciones y Consistencia", [
            "Impide el arranque de corridas de produccion con modelos no registrados previamente.",
            "Sincroniza automaticamente la relacion entre numero de parte del cliente y codigo interno.",
            "Garantiza que los herramentales requeridos coincidan con la especificacion del modelo."
        ])
    ],
    screenshot_filename="04_info_modelos_smt.png",
    caption_text="Catalogo y visor de especificaciones de modelos SMT"
)

# =============================================================================
# SLIDE 8: INGENIERIA - CONTROL DE BOM Y CAMBIOS ECO
# =============================================================================
add_standard_content_slide(
    slide_num=8,
    category="Ingenieria de Proceso",
    title="Listas de Materiales (BOM) y Control de Cambios ECO",
    subtitle="Gestion del arbol de componentes por tarjeta y seguimiento a ordenes de cambio de ingenieria",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Administrar la lista oficial de materiales (Bill of Materials) requerida para cada tarjeta electronica.",
            "Rastrear la posicion fisica exacta en el diseno del circuito (ej. C101, R204, U3) de cada componente.",
            "Gestionar las Ordenes de Cambio de Ingenieria (ECO) para sustituciones autorizadas."
        ]),
        ("Como Interactua el Usuario", [
            "El ingeniero de procesos importa el archivo BOM en formato Excel (.xlsx) validado.",
            "El sistema procesa la estructura, valida columnas requeridas y genera el arbol de componentes.",
            "Al emitir un cambio ECO, el sistema compara la version anterior vs la nueva y resalta diferencias."
        ]),
        ("Validaciones de Calidad y Bloqueo", [
            "Verificacion automatica de formato, evitando caracteres invalidos o numeros de parte inexistentes.",
            "Aprobacion requerida de calidad y produccion antes de autorizar la nueva revision en piso.",
            "Actualizacion instantanea de la lista de verificacion de alimentadores (feeders) de las maquinas."
        ])
    ],
    screenshot_filename="05_info_control_bom.png",
    caption_text="Modulo de administracion de BOM y ordenes de cambio de ingenieria (ECO)"
)

# =============================================================================
# SLIDE 9: CONTROL DE MATERIAL - INVENTARIO Y LOTES
# =============================================================================
add_standard_content_slide(
    slide_num=9,
    category="Control de Material",
    title="Inventario Actual de Almacen y Control de Lotes",
    subtitle="Monitoreo de stock de materia prima, trazabilidad por rollo/carrete y ubicacion en racks",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Monitorear en tiempo real el stock exacto de materias primas recibidas de proveedores.",
            "Identificar de manera unica cada carrete o caja mediante codigo unico de barras interno.",
            "Controlar las ubicaciones fisicas en almacen para una preparacion agil de kits de produccion."
        ]),
        ("Como Interactua el Usuario", [
            "Accede a 'Control de material' -> 'Inventario actual'.",
            "Aplica filtros por numero de parte, lote de proveedor, fecha de entrada o ubicacion.",
            "Consulta el desglose detallado por lote y exporta reportes estructurados a Excel con un clic."
        ]),
        ("Reglas de Negocio y Cuarentena", [
            "Identificacion automatica de lotes en cuarentena IQC, bloqueando su salida a lineas.",
            "Control de niveles de sensibilidad a la humedad (MSL) para componentes electronicos criticos.",
            "Soporte para trazabilidad inversa en caso de alertas de calidad de proveedores."
        ])
    ],
    screenshot_filename="06_material_inventario.png",
    caption_text="Pantalla de inventario actual de materia prima desglosado por lote"
)

# =============================================================================
# SLIDE 10: CONTROL DE MATERIAL - INVOICES Y VALUACION
# =============================================================================
add_standard_content_slide(
    slide_num=10,
    category="Control de Material",
    title="Facturacion (Invoices) y Valorizacion Financiera",
    subtitle="Conciliacion contable de recepciones fisicas, costos unitarios y valuacion de inventario",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Vincular las recepciones fisicas de componentes con las facturas comerciales (Invoices) emitidas.",
            "Determinar el costo unitario de compra y calcular el valor financiero total del inventario retenido.",
            "Facilitar el cruce contable entre compras, almacen y administracion de finanzas."
        ]),
        ("Como Interactua el Usuario", [
            "Selecciona 'Facturas / Invoice' para registrar o consultar facturas asociadas a pedidos.",
            "Ingresa al modulo 'Valorizacion de inventario' para auditar montos consolidados por categoria.",
            "Filtra por proveedor, fecha de emision o rango de facturacion para conciliaciones fiscales."
        ]),
        ("Calculos y Salidas Automatizadas", [
            "Calculo automatico de inventario valorizado por metodo de costos autorizado.",
            "Deteccion automatica de discrepancias entre cantidades facturadas vs recibidas fisicamente.",
            "Exportacion de reportes consolidados para auditorias contables y financieras."
        ])
    ],
    screenshot_filename="07_material_invoices.png",
    caption_text="Modulo de control de facturas comerciales (Invoices) y costeo de partes"
)

# =============================================================================
# SLIDE 11: CONTROL DE PRODUCCION - PLAN SMD DIARIO
# =============================================================================
add_standard_content_slide(
    slide_num=11,
    category="Control de Produccion",
    title="Programacion y Seguimiento del Plan SMD Diario",
    subtitle="Asignacion de ordenes de trabajo a lineas fisicas de SMT por fecha, turno y meta horaria",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Traducir las ordenes de fabricacion de clientes en programas diarios de produccion en lineas SMT.",
            "Balancear la carga de trabajo entre las lineas fisicas disponibles en la planta de montaje.",
            "Monitorear en tiempo real el cumplimiento de metas hora por hora durante el turno."
        ]),
        ("Como Interactua el Usuario", [
            "El planeador accede a 'Control de produccion' -> 'Plan SMD Diario'.",
            "Selecciona la fecha de corrida, la linea de produccion asignada y el modelo electronico.",
            "Configura la cantidad programada (WO) y la secuencia de fabricacion para el turno."
        ]),
        ("Reglas de Produccion e Interlock", [
            "Validacion previa de disponibilidad de componentes en almacen antes de autorizar el plan.",
            "Integracion automatica con los contadores de piezas terminadas de las maquinas en linea.",
            "Alertas operativas inmediatas ante desfases entre la meta teorica y las piezas reales producidas."
        ])
    ],
    screenshot_filename="08_produccion_plan_smd.png",
    caption_text="Interfaz de programacion y ejecucion del Plan SMD diario por linea"
)

# =============================================================================
# SLIDE 12: HERRAMIENTALES - METAL MASK (STENCILS) Y TENSION
# =============================================================================
add_standard_content_slide(
    slide_num=12,
    category="Control de Herramentales",
    title="Control de Metal Mask (Stencils) y Rasquetas",
    subtitle="Seguimiento de ciclos de uso, medicion de tension superficial y ubicacion en almacenes",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Controlar la vida util de las plantillas metalicas (stencils) para impresion de soldadura en pasta.",
            "Garantizar que la tension mecanica del marco se encuentre dentro de tolerancias de calidad.",
            "Rastrear la asignacion de rasquetas (squeegees) y la ubicacion en cajas de almacenamiento."
        ]),
        ("Como Interactua el Usuario", [
            "El operador escanea el codigo del stencil antes de montarlo en la maquina serigrafica (impresora).",
            "Registra las lecturas de tension en los puntos de control calibrados (medidos en N/cm).",
            "El sistema actualiza el conteo acumulado de ciclos de impresion tras cada turno."
        ]),
        ("Criterios de Rechazo y Seguridad", [
            "Bloqueo automatico del stencil en el sistema si la tension cae por debajo del minimo requerido.",
            "Alerta de vencimiento por superacion del limite maximo de ciclos de vida especificado.",
            "Prevencion de defectos de impresion (cortocircuitos o falta de soldadura) por desgaste de herramental."
        ])
    ],
    screenshot_filename="09_produccion_metal_mask.png",
    caption_text="Modulo de monitoreo de ciclos y tension de plantillas Metal Mask"
)

# =============================================================================
# SLIDE 13: MANTENIMIENTO - CUCHILLAS DE CORTE Y SOLDADURA
# =============================================================================
add_standard_content_slide(
    slide_num=13,
    category="Mantenimiento y Calidad",
    title="Control de Cuchillas de Corte y Pastas de Soldadura",
    subtitle="Monitoreo de desgaste en despanelizado y control termico de conservacion de soldadura",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Monitorear el desgaste de las cuchillas mecanicas utilizadas en el corte y separacion de paneles PCB.",
            "Controlar los tiempos de refrigeracion, atemperado y batido de los botes de pasta de soldadura.",
            "Asegurar la consistencia reologica de la pasta para evitar defectos de soldabilidad."
        ]),
        ("Como Interactua el Usuario", [
            "El tecnico registra el cambio de cuchilla y resetea el contador de cortes en el modulo.",
            "Al retirar pasta de refrigerador, escanea el bote y registra la hora de inicio de atemperado.",
            "El sistema calcula automaticamente el tiempo habilitado antes de que el quimico caduque en linea."
        ]),
        ("Validaciones y Prevencion", [
            "Alerta de mantenimiento preventivo al alcanzar el 90% de la vida util estimada de la cuchilla.",
            "Bloqueo de botes de soldadura que no hayan cumplido el tiempo minimo de estabilizacion termica.",
            "Prohibicion de uso en maquina si el bote ha superado el tiempo maximo de exposicion ambiental."
        ])
    ],
    screenshot_filename="10_produccion_cuchillas.png",
    caption_text="Control de contadores de cuchillas de corte y estandares de soldadura"
)

# =============================================================================
# SLIDE 14: CONTROL DE CALIDAD - LIBERACION OQC Y LQC
# =============================================================================
add_standard_content_slide(
    slide_num=14,
    category="Control de Calidad",
    title="Inspeccion en Linea (LQC) y Liberacion Saliente (OQC)",
    subtitle="Auditoria y liberacion formal de cajas de producto terminado previo a su envio a embarques",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Operar como compuerta de calidad estricta (Quality Gate) para producto terminado.",
            "Validar que cada caja armada cuente con inspeccion visual, funcional y empaque aprobado.",
            "Emitir el folio formal de liberacion OQC requerido por el almacen de embarques para recepcion."
        ]),
        ("Como Interactua el Usuario", [
            "El inspector de calidad OQC accede a la pantalla de liberacion y escanea el codigo de la caja.",
            "Registra los resultados del muestreo segun el plan de inspeccion y criterios AQL.",
            "Selecciona el dictamen: 'Aprobado / Released' o 'Rechazado / Cuarentena', sellando el registro."
        ]),
        ("Interlock con Modulo de Embarques", [
            "La base de datos actualiza el estatus en la tabla puente `oqc_release_boxes`.",
            "El modulo de embarques impide recibir cualquier caja que no cuente con liberacion OQC activa.",
            "Generacion automatica de certificados de calidad de lote para el cliente final."
        ])
    ],
    screenshot_filename="11_calidad_liberacion_oqc.png",
    caption_text="Historial y formulario de liberacion de calidad saliente (OQC)"
)

# =============================================================================
# SLIDE 15: METRICAS DE CALIDAD - TABLEROS PPMS
# =============================================================================
add_standard_content_slide(
    slide_num=15,
    category="Metricas y Analitica",
    title="Tableros PPMS: Monitoreo de Defectos en Partes Por Millon",
    subtitle="Analisis estadistico de defectos para recepcion (IQC), ensamble (LQC) y embarques (OQC)",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Proveer a la direccion y gerencia de calidad una vision cuantitativa del nivel de defectos en planta.",
            "Normalizar los indices de falla bajo el estandar internacional de Partes Por Millon (PPM).",
            "Identificar oportunamente variaciones de proceso y degradacion de componentes electronicos."
        ]),
        ("Como Interactua el Usuario", [
            "El usuario selecciona el tablero correspondiente: PPMs IQC, PPMs LQC o PPMs OQC.",
            "Configura el periodo de analisis (dia, semana, mes), linea de manufactura o modelo especifico.",
            "Analiza las graficas de Pareto y tablas comparativas para identificar las causas raiz prioritarias."
        ]),
        ("Toma de Decisiones y Acciones", [
            "Disparo de alertas automaticas si una linea sobrepasa el umbral objetivo de PPM corporativo.",
            "Soporte directo para la emision de acciones correctivas y solicitudes de analisis de 8 Disciplinas a proveedores.",
            "Historico exportable para revisiones de direccion y auditorias de certificacion IATF 16949."
        ])
    ],
    screenshot_filename="12_calidad_ppms.png",
    caption_text="Tablero analitico de calidad en partes por millon (PPMs OQC)"
)

# =============================================================================
# SLIDE 16: CONTROL DE CALIDAD - MASTER SAMPLE SMT
# =============================================================================
add_standard_content_slide(
    slide_num=16,
    category="Control de Calidad",
    title="Verificacion de Muestras Maestras (Master Sample SMT)",
    subtitle="Auditoria de primera pieza (Golden Sample) obligatoria en arranques y cambios de modelo",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Asegurar que la primera tarjeta producida en un turno o cambio de serie este 100% conforme.",
            "Verificar visual y dimensionalmente polaridad de diodos, valores de resistencias y alineacion.",
            "Eliminar el riesgo de fabricar lotes masivos con componentes invertidos o alimentadores erroneos."
        ]),
        ("Como Interactua el Usuario", [
            "Al iniciar una corrida, el operador retira la primera tarjeta armada y la entrega al auditor.",
            "El auditor abre el modulo 'Master Sample SMT', coteja contra el diagrama y aprueba punto por punto.",
            "Registra firmas de liberacion del operador de linea y del supervisor de calidad en turno."
        ]),
        ("Condicion de Interlock de Linea", [
            "La linea SMT queda autorizada para continuar a velocidad nominal unicamente tras la liberacion.",
            "Registro con marca temporal e identificacion de usuario responsable para fines de auditoria.",
            "Mantiene historial de inspecciones previas para consulta rapida ante dudas durante el turno."
        ])
    ],
    screenshot_filename="13_calidad_master_sample.png",
    caption_text="Modulo de registro e inspeccion de muestras maestras (Master Sample)"
)

# =============================================================================
# SLIDE 17: CONTROL DE RESULTADOS - INSPECCION OPTICA AOI
# =============================================================================
add_standard_content_slide(
    slide_num=17,
    category="Control de Resultados",
    title="Inspeccion Optica Automatica (AOI) y Analisis de Fallas",
    subtitle="Captura y clasificacion digital de fallas de soldadura, desalineacion y puentes de estaño",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Concentrar y analizar los registros generados por las maquinas de inspeccion optica automatica (AOI).",
            "Diferenciar de inmediato entre falsos rechazos de vision y defectos reales de soldadura.",
            "Monitorear la estabilidad termica del horno de reflujo y la precision de las montadoras."
        ]),
        ("Como Interactua el Usuario", [
            "El operador de estacion AOI revisa en pantalla el historial de tarjetas inspeccionadas por maquina.",
            "Confirma si la alerta corresponde a un defecto real (ej. corto, puente, componente ausente o levantado).",
            "Si es falla real, clasifica el defecto y deriva la tarjeta al modulo de reparacion correspondiente."
        ]),
        ("Optimizacion de Linea SMT", [
            "Mapeo de defectos recurrentes por designador de componente para correccion inmediata de feeders.",
            "Generacion de reportes consolidados por hora para el supervisor de produccion.",
            "Almacenamiento de registros para respaldar la calidad de cada lote ensamblado."
        ])
    ],
    screenshot_filename="14_resultados_aoi.png",
    caption_text="Historial y clasificacion de inspecciones de maquina optica AOI"
)

# =============================================================================
# SLIDE 18: CONTROL DE RESULTADOS - PRUEBAS ELECTRICAS ICT / FCT
# =============================================================================
add_standard_content_slide(
    slide_num=18,
    category="Control de Resultados",
    title="Pruebas Electricas en Circuito (ICT) y Funcionales (FCT)",
    subtitle="Historial de pruebas con cama de clavos y evaluacion electronica funcional parametrizada",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Registrar el resultado de pruebas electricas estaticas (ICT) y pruebas dinamicas funcionales (FCT).",
            "Validar valores de capacitancia, tolerancia de resistencias y ausencia de pistas abiertas o cortos.",
            "Garantizar que ninguna tarjeta con fallo electronico pueda pasar a la etapa de empaque final."
        ]),
        ("Como Interactua el Usuario", [
            "El probador ejecuta el ciclo de prueba automatica en la maquina correspondiente.",
            "El sistema MES registra el resultado por numero de serie: Pass (Aprobado) o Fail (Falla).",
            "El usuario consulta el dashboard de tasas de aprobacion (Pass/Fail Ratio) por linea y estacion."
        ]),
        ("Seguimiento y Control de Parametros", [
            "Auditoria de modificaciones en limites de prueba: cualquier ajuste de umbrales requiere autorizacion.",
            "Registro del designador especifico que provoco el fallo electrico para guiar la reparacion.",
            "Exportacion masiva de datos de prueba para analisis estadistico de dispersión CPK."
        ])
    ],
    screenshot_filename="15_resultados_ict.png",
    caption_text="Dashboard de resultados de pruebas electricas ICT y functional testing"
)

# =============================================================================
# SLIDE 19: CONTROL DE RESULTADOS - INVENTARIO DE REPARACION
# =============================================================================
add_standard_content_slide(
    slide_num=19,
    category="Control de Resultados",
    title="Inventario de Reparacion (SMD/ASSY) y Control de Scrap",
    subtitle="Trazabilidad de unidades en retrabajo, sustitucion de componentes y descarte de scrap",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Llevar un control estricto de las tarjetas retiradas de linea por fallas de AOI, ICT o funcionales.",
            "Evitar la perdida de material en proceso (WIP) en las estaciones tecnicas de retrabajo.",
            "Registrar las piezas no recuperables autorizadas para su baja formal como scrap."
        ]),
        ("Como Interactua el Usuario", [
            "El tecnico de reparacion escanea la tarjeta desviada y consulta el reporte de la prueba que fallo.",
            "Efectua el reemplazo del componente, registra la accion correctiva aplicada y el numero de parte usado.",
            "Re-envia la tarjeta al circuito de pruebas obligatorias para certificar su conformidad."
        ]),
        ("Validaciones y Prevencion de Fugas", [
            "Imposibilidad de empacar una tarjeta que tenga un estatus abierto de reparacion en sistema.",
            "Seguimiento de tiempos de estancia en reparacion para evitar rezago de producto.",
            "Clasificacion de causas de scrap para cobro de garantias a proveedores si la falla fue de componente."
        ])
    ],
    screenshot_filename="16_resultados_reparacion.png",
    caption_text="Control de stock de tarjetas en reparacion SMD y diagnostico tecnico"
)

# =============================================================================
# SLIDE 20: CONTROL DE PROCESO - ALMACEN DE EMBARQUES Y FIFO
# =============================================================================
add_standard_content_slide(
    slide_num=20,
    category="Logistica y Embarques",
    title="Almacen de Embarques y Motor de Despacho FIFO",
    subtitle="Recepcion de producto terminado, ubicaciones fisicas y despacho obligatorio por antiguedad",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Administrar las existencias fisicas de producto terminado empacado y listo para exportacion o cliente.",
            "Garantizar el cumplimiento estricto del principio First In, First Out (primeras entradas, primeras salidas).",
            "Eliminar el riesgo de despachar lotes recientes dejando cajas antiguas rezagadas en almacen."
        ]),
        ("Como Interactua el Usuario", [
            "El operador de embarques recibe las cajas liberadas por OQC y las ubica fisicamente en anaqueles.",
            "Al programar un embarque, ingresa el numero de parte y la cantidad solicitada por el cliente.",
            "El sistema genera la lista de despacho FIFO indicando exactamente que cajas escanear."
        ]),
        ("Motor Inteligente de Despacho", [
            "El algoritmo consulta las capas de entrada y bloquea el escaneo si no coincide con la caja mas antigua.",
            "Descarga automatica de inventario tras la confirmacion de carga en el transporte.",
            "Historial completo de movimientos de cajas para rastreo inmediato ante cualquier reclamacion."
        ])
    ],
    screenshot_filename="17_proceso_embarques.png",
    caption_text="Vista consolidada del inventario de producto terminado en embarques"
)

# =============================================================================
# SLIDE 21: CONTROL DE REPORTE - TRAZABILIDAD SERIALIZADA PCB
# =============================================================================
add_standard_content_slide(
    slide_num=21,
    category="Trazabilidad y Reportes",
    title="Trazabilidad Genealogica Unitaria por Serial de PCB",
    subtitle="Consulta integral del historial de manufactura de cada circuito electronico fabricado",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Ofrecer una auditoria instantanea y completa de la historia de cualquier tarjeta electronica individual.",
            "Cumplir con los requerimientos mas rigurosos de clientes automotrices e industriales de clase mundial.",
            "Contar con una herramienta de investigacion forense ante reclamos de garantia en campo."
        ]),
        ("Como Interactua el Usuario", [
            "El auditor o ingeniero introduce el numero de serie unico de la PCB en el campo de busqueda.",
            "El sistema recupera la genealogia completa: fecha y hora de fabricacion, linea, modelo y turno.",
            "Desglosa que lote de carrete alimento cada componente, que stencil aplico soldadura y quien inspecciono."
        ]),
        ("Valor Estrategico de Cumplimiento", [
            "Reduccion de tiempos de auditoria de dias a segundos mediante reportes consolidados exportables.",
            "Capacidad de delimitar acotadamente un recall a lotes especificos sin afectar toda la produccion.",
            "Garantia irrefutable del cumplimiento de estandares de calidad IPC e ISO/IATF."
        ])
    ],
    screenshot_filename="18_reporte_trazabilidad_pcb.png",
    caption_text="Reporte de trazabilidad serializada unitaria de componentes por PCB"
)

# =============================================================================
# SLIDE 22: MESA DE AYUDA - PORTAL DE TICKETS IT (/portal-tickets)
# =============================================================================
add_standard_content_slide(
    slide_num=22,
    category="Soporte y Mesa de Ayuda",
    title="Portal de Tickets e Incidentes Operativos en Planta",
    subtitle="Mesa de ayuda digital para atencion inmediata de incidentes de software, hardware y maquinaria",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Canalizar y dar seguimiento formal a fallas tecnicas que puedan interrumpir la operacion en planta.",
            "Evitar paros de linea prolongados mediante una comunicacion directa y registrada con soporte IT.",
            "Medir tiempos de respuesta (SLA) y resolucion de incidentes en equipos de piso."
        ]),
        ("Como Interactua el Usuario", [
            "El operador o supervisor redacta un ticket indicando departamento, linea afectada y prioridad.",
            "Puede adjuntar hasta 5 fotografias de evidencia directamente desde su dispositivo o terminal.",
            "Interactua mediante un hilo de mensajes en tiempo real con los ingenieros de soporte asignados."
        ]),
        ("Reglas de Prioridad y Resolucion", [
            "Clasificacion por impacto: Baja, Media, Alta o Critica (paro inminente de linea de ensamble).",
            "Soporte para 'Supertickets' institucionales de notificaciones obligatorias de superadministradores.",
            "Cierre documentado con causa raiz y solucion aplicada para enriquecer la base de conocimiento."
        ])
    ],
    screenshot_filename="18_tickets_portal.png",
    caption_text="Mesa de soporte IT y control de tickets operativos (URL: /portal-tickets)"
)

# =============================================================================
# SLIDE 23: GOBERNANZA - PANEL DE ADMINISTRACION Y AUDITORIA
# =============================================================================
add_standard_content_slide(
    slide_num=23,
    category="Gobernanza y Auditoria",
    title="Panel de Administracion y Bitacora de Auditoria",
    subtitle="Control granular de usuarios, matriz de permisos por boton y registro de acciones criticas",
    cards_data=[
        ("Objetivo y Funcion Operativa", [
            "Asegurar el control de accesos a nivel granular, impidiendo modificaciones no autorizadas en produccion.",
            "Administrar el directorio de colaboradores de la planta, sus departamentos y roles asignados.",
            "Mantener un registro inmutable (auditoria en tiempo real) de cada transaccion efectuada en el sistema."
        ]),
        ("Como Interactua el Usuario", [
            "El administrador gestiona altas, bajas y modificacion de roles y contrasenas de operadores.",
            "Configura la matriz de permisos activando o desactivando botones individuales de la interfaz.",
            "Consulta el modulo de auditoria para inspeccionar que usuario modifico un dato sensible, cuando y desde que IP."
        ]),
        ("Seguridad y Trazabilidad de Sistema", [
            "Invocacion automatica de `registrar_auditoria()` en cada evento de insercion, actualizacion o borrado.",
            "Separacion estricta de responsabilidades entre planeacion, calidad, almacen y administracion.",
            "Cumplimiento total con estandares de seguridad informatica y trazabilidad corporativa."
        ])
    ],
    screenshot_filename="20_admin_panel.png",
    caption_text="Consola de administracion de usuarios y roles (URL: /admin/panel)"
)

# =============================================================================
# SLIDE 24: CONCLUSIONES Y VALOR ESTRATEGICO
# =============================================================================
slide24 = prs.slides.add_slide(blank_layout)
add_header(slide24, "Conclusion Ejecutiva", "Impacto Operativo y Valor Estrategico de ILSAN MES", "Sintesis de los beneficios directos obtenidos en productividad, costo y satisfaccion de clientes")
add_footer(slide24, 24)

conclusions = [
    ("Blindaje de Calidad y Cero Defectos", [
        "Eliminacion de errores humanos gracias al Interlock automatico en maquinas y compuertas LQC/OQC.",
        "Aseguramiento de Golden Sample antes de producir cualquier lote masivo.",
        "Reduccion drastica del costo de no calidad y eliminacion de retrabajos innecesarios."
    ]),
    ("Trazabilidad Total y Cumplimiento", [
        "Capacidad de auditoria genealogica en tiempo real a nivel de componente individual en PCB.",
        "Cumplimiento garantizado con estandares automotrices e industriales de clase mundial.",
        "Respuesta inmediata y delimitada ante cualquier eventualidad de garantia o recall."
    ]),
    ("Disciplina Logistica y Reduccion de Costos", [
        "Control estricto de rotacion FIFO en producto terminado, evitando rezagos y obsolescencia.",
        "Monitoreo predictivo de desgaste de herramentales criticos (stencils de soldadura y cuchillas).",
        "Exactitud en inventarios de materia prima por rollo, eliminando descuadres en almacen."
    ]),
    ("Ecosistema Digital Unificado", [
        "Plataforma centralizada y robusta que conecta almacen, calidad, produccion y soporte IT.",
        "Navegacion agil, carga dinamica asincrona y soporte para terminales de mano industriales PDA.",
        "Escalabilidad garantizada para soportar el crecimiento sostenido de las lineas de fabricacion."
    ])
]

for idx, (c_title, c_points) in enumerate(conclusions):
    col = idx % 2
    row = idx // 2
    box_x = Inches(0.8 + col * 5.95)
    box_y = Inches(2.0 + row * 2.45)
    box_w = Inches(5.78)
    box_h = Inches(2.3)

    card_sh = slide24.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, box_x, box_y, box_w, box_h)
    card_sh.fill.solid()
    card_sh.fill.fore_color.rgb = COLOR_CARD_BG
    card_sh.line.color.rgb = COLOR_CARD_BORDER
    card_sh.line.width = Pt(1.5)

    tb_c = slide24.shapes.add_textbox(box_x + Inches(0.2), box_y + Inches(0.15), box_w - Inches(0.4), box_h - Inches(0.3))
    tf_c = tb_c.text_frame
    tf_c.word_wrap = True
    tf_c.margin_left = tf_c.margin_top = tf_c.margin_right = tf_c.margin_bottom = 0

    p_ct = tf_c.paragraphs[0]
    p_ct.text = c_title.upper()
    p_ct.font.name = 'Arial'
    p_ct.font.size = Pt(11.5)
    p_ct.font.bold = True
    p_ct.font.color.rgb = COLOR_PILL_TEXT

    for pt in c_points:
        p_pt = tf_c.add_paragraph()
        p_pt.text = f"- {pt}"
        p_pt.font.name = 'Calibri'
        p_pt.font.size = Pt(10)
        p_pt.font.color.rgb = COLOR_TEXT_MAIN
        p_pt.space_before = Pt(4)

# Save presentation
output_pptx_path = os.path.join(os.getcwd(), 'output', 'ILSAN_MES_Presentacion_Ejecutiva.pptx')
prs.save(output_pptx_path)
print(f"Presentation generated successfully with {len(prs.slides)} slides!")
print(f"File saved to: {output_pptx_path}")
