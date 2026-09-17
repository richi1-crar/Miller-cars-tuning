from flask import Flask, render_template, request, send_file, flash
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.units import cm
from email.message import EmailMessage
from dotenv import load_dotenv

import sqlite3
import smtplib
import os
from datetime import datetime


# =========================================================
# CONFIGURACIÓN
# =========================================================

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "cambia-esta-clave")

# Carpeta principal del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Base de datos
DB = os.path.join(BASE_DIR, "facturacion.db")

# Carpeta de PDFs
PDF_DIR = os.path.join(BASE_DIR, "facturas")
os.makedirs(PDF_DIR, exist_ok=True)

# Carpeta de archivos estáticos
STATIC_DIR = os.path.join(BASE_DIR, "static")


# =========================================================
# BASE DE DATOS
# =========================================================

def db():
    con = sqlite3.connect(
        DB,
        timeout=15
    )

    con.row_factory = sqlite3.Row

    # Ayuda a evitar bloqueos de SQLite
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=15000")

    return con


def init_db():
    con = db()

    con.execute("""
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero TEXT UNIQUE NOT NULL,
            fecha TEXT NOT NULL,
            cliente TEXT NOT NULL,
            correo TEXT NOT NULL,
            telefono TEXT,
            placa TEXT,
            vehiculo TEXT,
            subtotal REAL NOT NULL,
            descuento REAL NOT NULL,
            total REAL NOT NULL
        )
    """)

    con.commit()
    con.close()
# =========================================================
# TABLA DE GARANTÍAS
# =========================================================

def init_garantias():
    con = db()

    con.execute("""
        CREATE TABLE IF NOT EXISTS garantias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factura_numero TEXT,
            cliente TEXT NOT NULL,
            correo TEXT,
            telefono TEXT,
            placa TEXT,
            vehiculo TEXT,
            servicio TEXT,
            fecha_servicio TEXT,
            fecha_inicio TEXT,
            fecha_vencimiento TEXT,
            estado TEXT DEFAULT 'Vigente',
            observaciones TEXT
        )
    """)

    con.commit()
    con.close()

# =========================================================
# FORMATO DINERO
# =========================================================

def money(value):
    return "${:,.0f}".format(float(value)).replace(",", ".")


# =========================================================
# GENERAR PDF
# =========================================================

def generar_pdf(factura, items):
    ruta = os.path.join(
        PDF_DIR,
        f"Factura-{factura['numero']}.pdf"
    )

    doc = SimpleDocTemplate(
        ruta,
        pagesize=letter,
        rightMargin=32,
        leftMargin=32,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()

    # =====================================================
    # ESTILOS
    # =====================================================

    titulo_negro = ParagraphStyle(
        "TituloNegro",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=26,
        textColor=colors.HexColor("#111111")
    )

    titulo_rojo = ParagraphStyle(
        "TituloRojo",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=26,
        textColor=colors.HexColor("#e50914")
    )

    texto = ParagraphStyle(
        "Texto",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#222222")
    )

    texto_pequeno = ParagraphStyle(
        "TextoPequeno",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10
    )

    etiqueta = ParagraphStyle(
        "Etiqueta",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#555555")
    )

    gracias = ParagraphStyle(
        "Gracias",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=20,
        textColor=colors.HexColor("#e50914")
    )

    elementos = []

    # =====================================================
    # LOGO
    # =====================================================

    logo_path = os.path.join(
        "static",
        "logo.png"
    )

    if os.path.exists(logo_path):

        logo = Image(
            logo_path,
            width=8.8 * cm,
            height=3.0 * cm
        )

        logo.hAlign = "CENTER"

        elementos.append(logo)

    elementos.append(Spacer(1, 5))

    # =====================================================
    # TITULO + FECHA
    # =====================================================

    titulo = Table(
        [[
            [
                Paragraph("FACTURA", titulo_negro),
                Paragraph("DE SERVICIO", titulo_rojo)
            ],
            Paragraph(
                f"<b>FECHA</b><br/>"
                f"{factura['fecha']}",
                ParagraphStyle(
                    "Fecha",
                    parent=texto,
                    alignment=TA_CENTER,
                    fontSize=9,
                    leading=12
                )
            )
        ]],
        colWidths=[350, 130]
    )

    titulo.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),

        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    elementos.append(titulo)

    elementos.append(Spacer(1, 5))

    # =====================================================
    # NUMERO DE FACTURA
    # =====================================================

    numero = Table(
        [[
            Paragraph(
                f"N° {factura['numero']}",
                ParagraphStyle(
                    "NumeroFactura",
                    parent=texto,
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    textColor=colors.white,
                    alignment=TA_CENTER
                )
            )
        ]],
        colWidths=[145],
        rowHeights=[27]
    )

    numero.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1),
         colors.HexColor("#e50914")),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("BOX", (0, 0), (-1, -1),
         0.5,
         colors.HexColor("#e50914")),

        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))

    numero.hAlign = "RIGHT"

    elementos.append(numero)

    elementos.append(Spacer(1, 15))

    # =====================================================
    # DATOS DEL CLIENTE
    # =====================================================

    datos_cliente = [
        [
            Paragraph("CLIENTE", etiqueta),
            Paragraph("CORREO", etiqueta)
        ],
        [
            Paragraph(
                factura["cliente"] or "",
                texto
            ),
            Paragraph(
                factura["correo"] or "",
                texto
            )
        ],
        [
            Paragraph("TELÉFONO", etiqueta),
            Paragraph("PLACA", etiqueta)
        ],
        [
            Paragraph(
                factura["telefono"] or "",
                texto
            ),
            Paragraph(
                factura["placa"] or "",
                texto
            )
        ],
        [
            Paragraph("VEHÍCULO", etiqueta),
            Paragraph("SERVICIO", etiqueta)
        ],
        [
            Paragraph(
                factura["vehiculo"] or "",
                texto
            ),
            Paragraph(
                "Miller Cars Tuning",
                texto
            )
        ]
    ]

    cliente_table = Table(
        datos_cliente,
        colWidths=[240, 240],
        rowHeights=[
            19, 27,
            19, 27,
            19, 27
        ]
    )

    cliente_table.setStyle(TableStyle([

        # Fondo general
        ("BACKGROUND", (0, 0), (-1, -1),
         colors.HexColor("#f7f7f7")),

        # Encabezados
        ("BACKGROUND", (0, 0), (-1, 0),
         colors.HexColor("#eeeeee")),

        ("BACKGROUND", (0, 2), (-1, 2),
         colors.HexColor("#eeeeee")),

        ("BACKGROUND", (0, 4), (-1, 4),
         colors.HexColor("#eeeeee")),

        # Bordes
        ("GRID", (0, 0), (-1, -1),
         0.5,
         colors.HexColor("#d0d0d0")),

        # Línea central
        ("LINEBEFORE", (1, 0), (1, -1),
         1,
         colors.HexColor("#cccccc")),

        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),

        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    elementos.append(cliente_table)

    elementos.append(Spacer(1, 18))

    # =====================================================
    # TABLA DE SERVICIOS
    # =====================================================

    tabla_datos = [[
        "#",
        "DESCRIPCIÓN",
        "CANTIDAD",
        "PRECIO UNIT.",
        "TOTAL"
    ]]

    for i, item in enumerate(items, start=1):

        tabla_datos.append([
            str(i),
            Paragraph(
                item["descripcion"],
                texto
            ),
            str(item["cantidad"]),
            money(item["precio"]),
            money(
                item["cantidad"] *
                item["precio"]
            )
        ])

    tabla_servicios = Table(
        tabla_datos,
        colWidths=[
            35,
            240,
            70,
            85,
            85
        ],
        repeatRows=1
    )

    tabla_servicios.setStyle(TableStyle([

        # Cabecera
        ("BACKGROUND",
         (0, 0),
         (-1, 0),
         colors.HexColor("#111111")),

        ("TEXTCOLOR",
         (0, 0),
         (-1, 0),
         colors.white),

        ("FONTNAME",
         (0, 0),
         (-1, 0),
         "Helvetica-Bold"),

        # Cuerpo
        ("FONTNAME",
         (0, 1),
         (-1, -1),
         "Helvetica"),

        ("FONTSIZE",
         (0, 0),
         (-1, -1),
         8.5),

        ("GRID",
         (0, 0),
         (-1, -1),
         0.5,
         colors.HexColor("#cccccc")),

        # Alineación
        ("ALIGN",
         (0, 0),
         (0, -1),
         "CENTER"),

        ("ALIGN",
         (2, 1),
         (-1, -1),
         "RIGHT"),

        ("VALIGN",
         (0, 0),
         (-1, -1),
         "MIDDLE"),

        # Espaciado
        ("LEFTPADDING",
         (0, 0),
         (-1, -1),
         7),

        ("RIGHTPADDING",
         (0, 0),
         (-1, -1),
         7),

        ("TOPPADDING",
         (0, 0),
         (-1, -1),
         8),

        ("BOTTOMPADDING",
         (0, 0),
         (-1, -1),
         8),

        # Línea roja superior
        ("LINEABOVE",
         (0, 0),
         (-1, 0),
         3,
         colors.HexColor("#e50914")),
    ]))

    elementos.append(tabla_servicios)

    elementos.append(Spacer(1, 15))

    # =====================================================
    # PARTE INFERIOR
    # =====================================================

    # -------------------------
    # MENSAJE
    # -------------------------

    mensaje = [
        Paragraph("✓", ParagraphStyle(
            "Check",
            parent=texto,
            fontName="Helvetica-Bold",
            fontSize=25,
            textColor=colors.HexColor("#e50914"),
            alignment=TA_CENTER
        )),
        [
            Paragraph(
                "¡Gracias!",
                gracias
            ),
            Paragraph(
                "<b>Gracias por confiar en Miller Cars Tuning.</b><br/>"
                "Modificación de unidades y stops • "
                "Personalizaciones Tuning",
                texto_pequeno
            )
        ]
    ]

    mensaje_table = Table(
        [mensaje],
        colWidths=[45, 260]
    )

    mensaje_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),

        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # -------------------------
    # TOTALES
    # -------------------------

    totales = Table(
        [
            ["SUBTOTAL", money(factura["subtotal"])],
            ["DESCUENTO", money(factura["descuento"])],
            ["TOTAL", money(factura["total"])]
        ],
        colWidths=[120, 110],
        rowHeights=[27, 27, 34]
    )

    totales.setStyle(TableStyle([

        ("BACKGROUND",
         (0, 0),
         (-1, 1),
         colors.HexColor("#eeeeee")),

        ("BACKGROUND",
         (0, 2),
         (-1, 2),
         colors.HexColor("#e50914")),

        ("TEXTCOLOR",
         (0, 2),
         (-1, 2),
         colors.white),

        ("FONTNAME",
         (0, 0),
         (-1, -1),
         "Helvetica-Bold"),

        ("FONTSIZE",
         (0, 0),
         (-1, 1),
         8.5),

        ("FONTSIZE",
         (0, 2),
         (-1, 2),
         12),

        ("ALIGN",
         (1, 0),
         (1, -1),
         "RIGHT"),

        ("VALIGN",
         (0, 0),
         (-1, -1),
         "MIDDLE"),

        ("BOX",
         (0, 0),
         (-1, -1),
         0.5,
         colors.HexColor("#cccccc")),

        ("LEFTPADDING",
         (0, 0),
         (-1, -1),
         9),

        ("RIGHTPADDING",
         (0, 0),
         (-1, -1),
         9),
    ]))

    parte_inferior = Table(
        [[
            mensaje_table,
            totales
        ]],
        colWidths=[280, 230]
    )

    parte_inferior.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),

        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),

        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    elementos.append(parte_inferior)

    elementos.append(Spacer(1, 18))

    # =====================================================
    # PIE CORPORATIVO
    # =====================================================

    footer = Table(
        [[
            Paragraph(
                "<b>Bogota</b><br/>"
                "Cra. 18 #3a 27, Bogotá",
                ParagraphStyle(
                    "Footer1",
                    parent=texto_pequeno,
                    textColor=colors.white
                )
            ),

            Paragraph(
                "<b>PEDIDOS Y COTIZACIONES</b><br/>"
                "+57 301 6144438",
                ParagraphStyle(
                    "Footer2",
                    parent=texto_pequeno,
                    textColor=colors.white
                )
            ),

            Paragraph(
                "<b>MILLER CARS TUNING</b><br/>"
                "Facebook • Instagram • TikTok",
                ParagraphStyle(
                    "Footer3",
                    parent=texto_pequeno,
                    textColor=colors.white
                )
            )
        ]],
        colWidths=[170, 170, 170],
        rowHeights=[55]
    )

    footer.setStyle(TableStyle([

        ("BACKGROUND",
         (0, 0),
         (-1, -1),
         colors.HexColor("#0b0b0b")),

        ("TEXTCOLOR",
         (0, 0),
         (-1, -1),
         colors.white),

        ("LINEBEFORE",
         (1, 0),
         (1, 0),
         1,
         colors.HexColor("#e50914")),

        ("LINEBEFORE",
         (2, 0),
         (2, 0),
         1,
         colors.HexColor("#e50914")),

        ("VALIGN",
         (0, 0),
         (-1, -1),
         "MIDDLE"),

        ("LEFTPADDING",
         (0, 0),
         (-1, -1),
         10),

        ("RIGHTPADDING",
         (0, 0),
         (-1, -1),
         10),
    ]))

    elementos.append(footer)

    # =====================================================
    # CREAR PDF
    # =====================================================

    doc.build(elementos)

    return ruta
    # =====================================================
    # INFORMACIÓN DEL CLIENTE
    # =====================================================

    info = [
        [
            "Factura",
            factura["numero"],
            "Fecha",
            factura["fecha"]
        ],

        [
            "Cliente",
            factura["cliente"],
            "Correo",
            factura["correo"]
        ],

        [
            "Teléfono",
            factura["telefono"] or "",
            "Placa",
            factura["placa"] or ""
        ],

        [
            "Vehículo",
            factura["vehiculo"] or "",
            "",
            ""
        ],
    ]


    t = Table(
        info,
        colWidths=[
            75,
            190,
            65,
            160
        ]
    )


    t.setStyle(
        TableStyle([
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.whitesmoke
            ),

            (
                "BACKGROUND",
                (2, 0),
                (2, -1),
                colors.whitesmoke
            ),

            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "FONTNAME",
                (2, 0),
                (2, -1),
                "Helvetica-Bold"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                8.5
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "SPAN",
                (1, 3),
                (3, 3)
            ),
        ])
    )

    elementos.append(t)

    elementos.append(
        Spacer(1, 15)
    )


    # =====================================================
    # SERVICIOS
    # =====================================================

    data = [
        [
            "Descripción",
            "Cantidad",
            "Precio",
            "Total"
        ]
    ]


    for item in items:

        data.append(
            [
                item["descripcion"],
                str(item["cantidad"]),
                money(item["precio"]),
                money(
                    item["cantidad"] *
                    item["precio"]
                )
            ]
        )


    tabla = Table(
        data,
        colWidths=[
            270,
            65,
            80,
            85
        ]
    )


    tabla.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#222222")
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "ALIGN",
                (1, 1),
                (-1, -1),
                "RIGHT"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                9
            ),

            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#f5f5f5")
                ]
            ),
        ])
    )


    elementos.append(tabla)

    elementos.append(
        Spacer(1, 12)
    )


    # =====================================================
    # TOTALES
    # =====================================================

    totales = [
        [
            "Subtotal",
            money(factura["subtotal"])
        ],

        [
            "Descuento",
            money(factura["descuento"])
        ],

        [
            "TOTAL",
            money(factura["total"])
        ],
    ]


    tt = Table(
        totales,
        colWidths=[
            130,
            100
        ],
        hAlign="RIGHT"
    )


    tt.setStyle(
        TableStyle([
            (
                "ALIGN",
                (1, 0),
                (1, -1),
                "RIGHT"
            ),

            (
                "FONTNAME",
                (0, 2),
                (-1, 2),
                "Helvetica-Bold"
            ),

            (
                "FONTSIZE",
                (0, 0),
                (-1, -1),
                10
            ),

            (
                "LINEABOVE",
                (0, 2),
                (-1, 2),
                1,
                colors.black
            ),
        ])
    )


    elementos.append(tt)

    elementos.append(
        Spacer(1, 18)
    )


    elementos.append(
        Paragraph(
            "Gracias por confiar en Miller Cars Tuning.",
            styles["CenterSmall"]
        )
    )

    elementos.append(
        Paragraph(
            "Modificación de unidades y stops • "
            "Personalizaciones Tuning",
            styles["CenterSmall"]
        )
    )


    # =====================================================
    # CREAR PDF
    # =====================================================

    doc.build(elementos)

    return ruta


# =========================================================
# ENVIAR CORREO
# =========================================================

def enviar_correo(destino, numero, ruta_pdf):

    remitente = os.getenv("MAIL_USER")
    password = os.getenv("MAIL_PASSWORD")


    if not remitente or not password:

        raise RuntimeError(
            "Falta configurar MAIL_USER y MAIL_PASSWORD "
            "en el archivo .env"
        )


    msg = EmailMessage()

    msg["Subject"] = (
        f"Factura {numero} - Miller Cars Tuning"
    )

    msg["From"] = remitente
    msg["To"] = destino


    msg.set_content(
        "Hola,\n\n"
        "Adjuntamos la factura de servicio de "
        "Miller Cars Tuning "
        f"correspondiente a la factura {numero}.\n\n"
        "Gracias por confiar en nosotros.\n\n"
        "Miller Cars Tuning"
    )


    # Adjuntar PDF
    with open(ruta_pdf, "rb") as f:

        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="pdf",
            filename=os.path.basename(ruta_pdf)
        )


    host = os.getenv(
        "SMTP_HOST",
        "smtp.gmail.com"
    )

    port = int(
        os.getenv(
            "SMTP_PORT",
            "587"
        )
    )


    # Conexión con Gmail
    with smtplib.SMTP(
        host,
        port,
        timeout=30
    ) as smtp:

        smtp.ehlo()

        smtp.starttls()

        smtp.ehlo()

        smtp.login(
            remitente,
            password
        )

        smtp.send_message(msg)


# =========================================================
# PÁGINA PRINCIPAL
# =========================================================

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        try:

            # =================================================
            # DATOS DEL CLIENTE
            # =================================================

            cliente = request.form["cliente"].strip()

            correo = request.form["correo"].strip()

            telefono = request.form.get(
                "telefono",
                ""
            ).strip()

            placa = request.form.get(
                "placa",
                ""
            ).strip().upper()

            vehiculo = request.form.get(
                "vehiculo",
                ""
            ).strip()

            descuento = float(
                request.form.get(
                    "descuento",
                    "0"
                ) or 0
            )


            # =================================================
            # SERVICIOS
            # =================================================

            descripciones = request.form.getlist(
                "descripcion[]"
            )

            cantidades = request.form.getlist(
                "cantidad[]"
            )

            precios = request.form.getlist(
                "precio[]"
            )


            items = []

            subtotal = 0


            for d, c, p in zip(
                descripciones,
                cantidades,
                precios
            ):

                if not d.strip():
                    continue


                cantidad = float(
                    c or 0
                )

                precio = float(
                    p or 0
                )


                total_item = (
                    cantidad * precio
                )

                subtotal += total_item


                items.append(
                    {
                        "descripcion": d.strip(),
                        "cantidad": cantidad,
                        "precio": precio
                    }
                )


            total = max(
                0,
                subtotal - descuento
            )


            # =================================================
            # GUARDAR FACTURA
            # =================================================

            con = db()

            try:

                siguiente = con.execute(
                    """
                    SELECT COALESCE(MAX(id), 0) + 1
                    FROM facturas
                    """
                ).fetchone()[0]


                numero = (
                    f"MCT-{siguiente:06d}"
                )


                fecha = datetime.now().strftime(
                    "%d/%m/%Y %H:%M"
                )


                con.execute(
                    """
                    INSERT INTO facturas
                    (
                        numero,
                        fecha,
                        cliente,
                        correo,
                        telefono,
                        placa,
                        vehiculo,
                        subtotal,
                        descuento,
                        total
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,

                    (
                        numero,
                        fecha,
                        cliente,
                        correo,
                        telefono,
                        placa,
                        vehiculo,
                        subtotal,
                        descuento,
                        total
                    )
                )


                con.commit()


                factura = con.execute(
                    """
                    SELECT *
                    FROM facturas
                    WHERE numero=?
                    """,
                    (numero,)
                ).fetchone()


            finally:

                # IMPORTANTE:
                # liberar SQLite inmediatamente
                con.close()


            # =================================================
            # GENERAR PDF
            # =================================================

            ruta = generar_pdf(
                factura,
                items
            )


            # =================================================
            # ENVIAR CORREO
            # =================================================

            try:

                enviar_correo(
                    correo,
                    numero,
                    ruta
                )


                flash(
                    f"Factura {numero} creada y enviada "
                    f"a {correo}.",
                    "ok"
                )


            except Exception as e:

                flash(
                    f"Factura {numero} creada, pero "
                    f"no se pudo enviar el correo: {e}",
                    "error"
                )


            # =================================================
            # DESCARGAR PDF
            # =================================================

            return send_file(
                ruta,
                as_attachment=True
            )


        except Exception as e:

            flash(
                f"Error al generar la factura: {e}",
                "error"
            )

            return render_template(
                "index.html"
            )


    return render_template(
        "index.html"
    )


# =========================================================
# LISTADO DE FACTURAS
# =========================================================

@app.route("/facturas")
def facturas():

    con = db()

    try:

        rows = con.execute(
            """
            SELECT *
            FROM facturas
            ORDER BY id DESC
            """
        ).fetchall()

    finally:

        con.close()


    return render_template(
        "facturas.html",
        facturas=rows
    )


# =========================================================
# VER / DESCARGAR PDF
# =========================================================

@app.route("/pdf/<numero>")
def pdf(numero):

    ruta = os.path.join(
        PDF_DIR,
        f"Factura-{numero}.pdf"
    )


    if not os.path.exists(ruta):

        return "PDF no encontrado", 404


    return send_file(
        ruta,
        as_attachment=True
    )

# =========================================================
# CLIENTES Y GARANTÍAS
# =========================================================

@app.route("/garantias", methods=["GET", "POST"])
def garantias():

    con = db()

    if request.method == "POST":

        cliente = request.form.get("cliente", "").strip()
        correo = request.form.get("correo", "").strip()
        telefono = request.form.get("telefono", "").strip()
        placa = request.form.get("placa", "").strip().upper()
        vehiculo = request.form.get("vehiculo", "").strip()
        factura_numero = request.form.get("factura_numero", "").strip()
        servicio = request.form.get("servicio", "").strip()

        fecha_servicio = request.form.get(
            "fecha_servicio", ""
        )

        fecha_inicio = request.form.get(
            "fecha_inicio", ""
        )

        fecha_vencimiento = request.form.get(
            "fecha_vencimiento", ""
        )

        observaciones = request.form.get(
            "observaciones", ""
        ).strip()

        con.execute("""
            INSERT INTO garantias (
                factura_numero,
                cliente,
                correo,
                telefono,
                placa,
                vehiculo,
                servicio,
                fecha_servicio,
                fecha_inicio,
                fecha_vencimiento,
                estado,
                observaciones
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            factura_numero,
            cliente,
            correo,
            telefono,
            placa,
            vehiculo,
            servicio,
            fecha_servicio,
            fecha_inicio,
            fecha_vencimiento,
            "Vigente",
            observaciones
        ))

        con.commit()
        con.close()

        flash(
            "Garantía registrada correctamente.",
            "ok"
        )

        return redirect("/garantias")

    # Actualizar garantías vencidas

    hoy = datetime.now().strftime("%Y-%m-%d")

    con.execute("""
        UPDATE garantias
        SET estado = 'Vencida'
        WHERE fecha_vencimiento < ?
    """, (hoy,))

    con.execute("""
        UPDATE garantias
        SET estado = 'Vigente'
        WHERE fecha_vencimiento >= ?
    """, (hoy,))

    con.commit()

    clientes = con.execute("""
        SELECT *
        FROM garantias
        ORDER BY fecha_vencimiento ASC
    """).fetchall()

    facturas = con.execute("""
        SELECT *
        FROM facturas
        ORDER BY id DESC
    """).fetchall()

    con.close()

    return render_template(
        "garantias.html",
        clientes=clientes,
        facturas=facturas
    )
# =========================================================
# INICIAR SERVIDOR
# =========================================================
if __name__ == "__main__":

    init_db()
    init_garantias()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )