import os
import csv
import json
import re
import threading
from docx import Document
from pypdf import PdfReader
import google.generativeai as genai
import google.api_core.exceptions as api_exceptions

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QTextEdit,
    QPushButton, QFileDialog, QCheckBox, QProgressBar, QMessageBox,
    QHBoxLayout, QFrame, QPlainTextEdit, QStackedWidget, QGroupBox
)
from PySide6.QtCore import Signal, QObject, Qt, QThread
from PySide6.QtGui import QIcon


# ----------------------------
# Señales para actualizar la UI desde un hilo
# ----------------------------
class WorkerSignals(QObject):
    progress_max = Signal(int)
    progress = Signal(int)
    summary = Signal(list)
    info = Signal(str)
    error = Signal(str)
    enable_run = Signal(bool)


signals = WorkerSignals()


# ----------------------------
# Utilidades de lectura
# ----------------------------
def listar_archivos(carpeta):
    exts = (".docx", ".pdf")
    archivos = []
    for f in os.listdir(carpeta):
        if f.lower().endswith(exts):
            archivos.append(os.path.join(carpeta, f))
    return archivos


def leer_docx(path):
    try:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        return ""


def leer_pdf(path):
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            t = page.extract_text() or ""
            text += t + "\n"
        return text.strip()
    except Exception:
        return ""


def leer_requerimiento(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return leer_docx(path)
    if ext == ".pdf":
        return leer_pdf(path)
    return ""


# ----------------------------
# IA (Gemini) - Mejorado
# ----------------------------
def _extraer_json_array(texto):
    s = (texto or "").strip()
    s = re.sub(r"^```(?:json)?\s*", "", s)
    s = re.sub(r"\s*```$", "", s)
    i, j = s.find("["), s.rfind("]")
    if i != -1 and j != -1 and j > i:
        s = s[i:j + 1]
    s = re.sub(r",\s*([\]}])", r"\1", s)
    try:
        return json.loads(s)
    except Exception:
        return []


def generar_casos_gemini(api_key, requerimiento, contexto_general, flujo_proceso, tipos_prueba):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        # Prompt mejorado sin limitaciones artificiales
        prompt_base = """Eres un experto en Testing y Quality Assurance con experiencia en análisis de requerimientos y diseño de casos de prueba.

TAREA: Analizar el siguiente requerimiento y generar casos de prueba completos para lograr la MÁXIMA COBERTURA posible.

FORMATO DE RESPUESTA: Devuelve ÚNICAMENTE un array JSON válido con objetos que contengan exactamente estas claves:
- `id_caso_prueba`: un identificador único (ej. "TC001").
- `titulo_caso_prueba`: una descripción concisa.
- `Descripcion`: una descripción detallada.
- `Precondiciones`: los requisitos para ejecutar el caso de prueba.
- "Tipo_de_prueba": (string) "Funcional" o "No Funcional"
- "Nivel_de_prueba": (string) "UAT"
- "Tipo_de_ejecucion": (string) "Manual"
- `Pasos`: un array de strings que describen los pasos para ejecutar la prueba.
- `Resultado_esperado`: un array de strings que describe lo que se espera que suceda al finalizar los pasos.
- `Categoria`: (string) Para funcionales: "Flujo Principal", "Flujos Alternativos", "Casos Límite", "Casos de Error". Para no funcionales: "Rendimiento", "Seguridad", "Usabilidad", "Compatibilidad", "Confiabilidad"
- "Ambiente": (string) "QA"
- "Ciclo": (string) "Ciclo 1"
- "issuetype": (string) "Test Case"
- `Prioridad`: la importancia del caso de prueba (ej. 'Alta', 'Media', 'Baja').

El JSON debe ser un array que contenga todos los casos de prueba generados. No incluyas ningún texto o explicación adicional fuera del objeto JSON."""

        # Construir prompt basado en tipos seleccionados
        incluir_funcionales = "funcional" in tipos_prueba
        incluir_no_funcionales = "no_funcional" in tipos_prueba

        if incluir_funcionales and incluir_no_funcionales:
            prompt_especifico = """
TIPOS DE PRUEBAS A GENERAR (COBERTURA COMPLETA SIN LÍMITES):

PASO 1 - ANÁLISIS DEL REQUERIMIENTO:
Analiza el requerimiento para entender qué aspectos necesitan cobertura:

ASPECTOS FUNCIONALES a cubrir si están presentes:
- Flujos de trabajo y casos de uso
- Validaciones y transformaciones de datos
- Reglas de negocio y lógica
- Interacciones y integraciones
- Manejo de errores y excepciones

ASPECTOS NO FUNCIONALES a cubrir si están presentes:
- Rendimiento (tiempo, carga, throughput, escalabilidad)
- Seguridad (autenticación, autorización, protección de datos)
- Usabilidad (experiencia de usuario, accesibilidad)
- Compatibilidad (plataformas, navegadores, dispositivos)
- Confiabilidad (disponibilidad, recuperación, integridad)

PASO 2 - GENERACIÓN DE CASOS:
Para CADA aspecto identificado, genera TODOS los casos necesarios para cobertura completa:

PRUEBAS FUNCIONALES (genera si hay aspectos funcionales):
- Todos los flujos principales y alternativos
- Todas las validaciones de entrada requeridas
- Todos los casos límite y condiciones borde
- Todos los escenarios de error posibles
- Todas las integraciones con otros componentes

PRUEBAS NO FUNCIONALES (genera si hay aspectos no funcionales):
- Todos los escenarios de carga y rendimiento relevantes
- Todos los vectores de seguridad aplicables
- Todos los contextos de usabilidad necesarios
- Todas las combinaciones de compatibilidad críticas
- Todos los escenarios de fallo y recuperación

PRINCIPIO FUNDAMENTAL:
- La COBERTURA COMPLETA determina la cantidad de casos, no límites artificiales
- Genera casos hasta cubrir exhaustivamente cada aspecto del requerimiento
- Si un requerimiento es 100% de seguridad, genera 100% casos de seguridad
- Si un requerimiento es 100% funcional, genera 100% casos funcionales
- Si es mixto, cubre proporcionalmente según la complejidad de cada aspecto"""
        elif incluir_funcionales:
            prompt_especifico = """
TIPOS DE PRUEBAS A GENERAR (COBERTURA FUNCIONAL COMPLETA):

PRUEBAS FUNCIONALES:
   - Flujo principal y todos los casos exitosos
   - Flujos alternativos y rutas de excepción
   - Validación exhaustiva de campos y datos
   - Casos límite, condiciones borde y extremas
   - Manejo completo de errores y excepciones
   - Estados del sistema y transiciones
   - Integración con componentes relacionados

PRINCIPIO DE COBERTURA MÁXIMA:
- Genera TODOS los casos funcionales necesarios para cobertura completa
- No te limites por cantidad, prioriza la cobertura exhaustiva
- Incluye casos para cada condición, rama y escenario posible"""
        elif incluir_no_funcionales:
            prompt_especifico = """
TIPOS DE PRUEBAS A GENERAR (COBERTURA NO FUNCIONAL COMPLETA):

PRUEBAS NO FUNCIONALES:
   - RENDIMIENTO: Carga normal, picos, estrés, volumen, tiempo de respuesta
   - SEGURIDAD: Autenticación, autorización, validación, ataques, cifrado
   - USABILIDAD: Navegación, accesibilidad, experiencia, interfaces
   - COMPATIBILIDAD: Múltiples entornos, navegadores, dispositivos, versiones
   - CONFIABILIDAD: Disponibilidad, recuperación, integridad, tolerancia a fallos

PRINCIPIO DE COBERTURA MÁXIMA:
- Genera TODOS los casos no funcionales relevantes para el requerimiento
- Especifica métricas precisas y medibles
- Considera todos los contextos de uso y condiciones operativas"""
        else:
            return []  # Si no se selecciona ningún tipo

        prompt_contexto = f"""
CONTEXTO DEL PROYECTO:
{contexto_general}

FLUJO DEL PROCESO:
{flujo_proceso}

REQUERIMIENTO A ANALIZAR:
{requerimiento}

INSTRUCCIONES FINALES:
- Responde SOLO con el array JSON, sin texto adicional
- Cada caso debe ser único y aportar valor específico
- Los pasos deben ser claros y ejecutables por cualquier tester
- Los resultados esperados deben ser verificables y específicos
"""

        prompt_completo = prompt_base + prompt_especifico + prompt_contexto

        response = model.generate_content(prompt_completo)
        texto = getattr(response, "text", "") or ""
        return _extraer_json_array(texto)
    except Exception as e:
        print(f"Error en generar_casos_gemini: {e}")
        return []


# ----------------------------
# Guardado CSV - Mejorado para el nuevo formato
# ----------------------------
def guardar_csv(casos, output_path):
    try:
        # Define las columnas en el orden exacto del prompt
        fieldnames = [
            "id_caso_prueba",
            "titulo_caso_prueba",
            "Descripcion",
            "Precondiciones",
            "Tipo_de_prueba",
            "Nivel_de_prueba",
            "Tipo_de_ejecucion",
            "Pasos",
            "Resultado_esperado",
            "Categoria",
            "Ambiente",
            "Ciclo",
            "issuetype",
            "Prioridad"
        ]

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for c in casos:
                # Normaliza las claves a las del prompt si difieren
                row = {
                    "id_caso_prueba": c.get("id_caso_prueba", ""),
                    "titulo_caso_prueba": c.get("titulo_caso_prueba", ""),
                    "Descripcion": c.get("Descripcion", ""),
                    "Precondiciones": c.get("Precondiciones", ""),
                    "Tipo_de_prueba": c.get("Tipo_de_prueba", ""),
                    "Nivel_de_prueba": c.get("Nivel_de_prueba", ""),
                    "Tipo_de_ejecucion": c.get("Tipo_de_ejecucion", ""),
                    # Convierte arrays de pasos y resultados a strings con " | "
                    "Pasos": " | ".join(c.get("Pasos", [])),
                    "Resultado_esperado": " | ".join(c.get("Resultado_esperado", [])),
                    "Categoria": c.get("Categoria", ""),
                    "Ambiente": c.get("Ambiente", ""),
                    "Ciclo": c.get("Ciclo", ""),
                    "issuetype": c.get("issuetype", ""),
                    "Prioridad": c.get("Prioridad", ""),
                }
                writer.writerow(row)
        return True
    except Exception as e:
        print(f"Error guardando CSV: {e}")
        return False


# ----------------------------
# Proceso en hilo - Mejorado
# ----------------------------
def procesar_en_hilo(input_dir, output_dir, api_key, contexto, flujo, tipos_prueba):
    archivos = listar_archivos(input_dir)
    if not archivos:
        signals.info.emit("No se encontraron .docx/.pdf en la carpeta seleccionada.")
        return

    total = len(archivos)
    signals.progress_max.emit(total)
    signals.progress.emit(0)
    signals.enable_run.emit(False)

    resumen = []
    casos_funcionales_total = 0
    casos_no_funcionales_total = 0

    for i, path in enumerate(archivos, start=1):
        nombre = os.path.basename(path)
        texto = leer_requerimiento(path)
        if not texto:
            resumen.append(f"{nombre} → 0 casos (sin contenido)")
            signals.progress.emit(i)
            continue

        casos = generar_casos_gemini(api_key, texto, contexto, flujo, tipos_prueba) or []

        # Contar tipos de casos
        funcionales = len([c for c in casos if c.get("Tipo_de_prueba", "").lower() == "funcional"])
        no_funcionales = len([c for c in casos if c.get("Tipo_de_prueba", "").lower() == "no funcional"])

        casos_funcionales_total += funcionales
        casos_no_funcionales_total += no_funcionales

        conteo = len(casos)
        nombre_base = os.path.splitext(nombre)[0]
        out_path = os.path.join(output_dir, f"{nombre_base}_matriz.csv")

        if conteo > 0:
            guardar_csv(casos, out_path)

        # Mostrar detalle según tipos seleccionados
        if "funcional" in tipos_prueba and "no_funcional" in tipos_prueba:
            resumen.append(f"{nombre} → {conteo} casos ({funcionales}F + {no_funcionales}NF)")
        elif "funcional" in tipos_prueba:
            resumen.append(f"{nombre} → {funcionales} casos funcionales")
        elif "no_funcional" in tipos_prueba:
            resumen.append(f"{nombre} → {no_funcionales} casos no funcionales")

        signals.progress.emit(i)

    # Resumen final
    resumen.append("")
    resumen.append("=== RESUMEN TOTAL ===")
    resumen.append(f"Archivos procesados: {len(archivos)}")

    if "funcional" in tipos_prueba:
        resumen.append(f"Casos funcionales: {casos_funcionales_total}")
    if "no_funcional" in tipos_prueba:
        resumen.append(f"Casos no funcionales: {casos_no_funcionales_total}")

    resumen.append(f"Total de casos: {casos_funcionales_total + casos_no_funcionales_total}")

    signals.summary.emit(resumen)
    signals.enable_run.emit(True)
    signals.info.emit("Proceso completado exitosamente.")


# ----------------------------
# UI principal como QWidget - Mejorado
# ----------------------------
class GeneradorMatrices(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.setWindowTitle("Generador de Matrices de Pruebas (IA)")
        self.resize(900, 850)
        self.stacked_widget = stacked_widget

        # --- Estilos Locales ---
        self.setStyleSheet("""
            QWidget {
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #0F0F23, stop: 1 #1A1A2E);
                color: #F5F5F5;
                font-family: 'Segoe UI';
                font-size: 14px;
            }
            QFrame {
                background-color: #2A2A40;
                border-radius: 12px;
                border: 1px solid #3C3C5C;
            }
            QGroupBox {
                background-color: #2A2A40;
                border-radius: 12px;
                border: 1px solid #3C3C5C;
                font-weight: bold;
                color: #B0C4DE;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #B0C4DE;
            }
            QLineEdit, QTextEdit, QPlainTextEdit {
                background-color: #3A3A50;
                border: 1px solid #5C5C7A;
                color: #F5F5F5;
                border-radius: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #3F51B5;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5C6BC0;
            }
            QProgressBar {
                background-color: #2A2A40;
                border: 1px solid #3C3C5C;
                border-radius: 5px;
                text-align: center;
                color: #F5F5F5;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 5px;
            }
            QCheckBox {
                color: #B0C4DE;
                font-size: 13px;
                padding: 8px;
                background-color: #3A3A50;
                border: 1px solid #5C5C7A;
                border-radius: 8px;
                margin: 2px;
            }
            QCheckBox:hover {
                background-color: #4A4A60;
                border-color: #6C6C8A;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3A3A50;
                border: 1px solid #5C5C7A;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 3px;
            }
        """)

        layout = QVBoxLayout(self)

        # ---- Botón de Home (casita) ----
        btn_home = QPushButton("🏠 Menú Principal")
        btn_home.setFixedSize(150, 40)
        btn_home.setStyleSheet("""
            QPushButton {
                background-color: #3F51B5;
                color: white;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5C6BC0;
            }
        """)
        btn_home.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        lbl_appname = QLabel("🚀 TestCreator")
        lbl_appname.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFD700;margin-right: 100px;")

        top_bar = QHBoxLayout()
        top_bar.addWidget(btn_home, alignment=Qt.AlignLeft)
        top_bar.addStretch()
        top_bar.addWidget(lbl_appname, alignment=Qt.AlignCenter)
        top_bar.addStretch()

        layout.addLayout(top_bar)

        # ---- Card configuración ----
        config_card = QFrame()
        config_card.setFrameShape(QFrame.StyledPanel)
        config_layout = QVBoxLayout(config_card)

        lbl_title = QLabel("⚙️ Configuración")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        config_layout.addWidget(lbl_title)

        # Carpeta entrada
        row_in = QHBoxLayout()
        self.entry_input = QLineEdit()
        self.entry_input.setPlaceholderText("Da click en el botón 'seleccionar' para colocar la ruta")
        btn_in = QPushButton("Seleccionar")
        btn_in.clicked.connect(self.seleccionar_in)
        row_in.addWidget(QLabel("Carpeta de Requerimientos:"))
        row_in.addWidget(self.entry_input)
        row_in.addWidget(btn_in)
        config_layout.addLayout(row_in)

        # Carpeta salida
        row_out = QHBoxLayout()
        self.entry_output = QLineEdit()
        self.entry_output.setPlaceholderText("Da click en el botón 'seleccionar' para colocar la ruta")
        btn_out = QPushButton("Seleccionar")
        btn_out.clicked.connect(self.seleccionar_out)
        row_out.addWidget(QLabel("Carpeta de Salida:"))
        row_out.addWidget(self.entry_output)
        row_out.addWidget(btn_out)
        config_layout.addLayout(row_out)

        # API Key
        row_api = QHBoxLayout()
        self.entry_api = QLineEdit()
        self.entry_api.setPlaceholderText("Ejemplo: AIzaSyD3x-xxxx-xxxx-xxxx-xxxxx")
        self.entry_api.setEchoMode(QLineEdit.Password)
        row_api.addWidget(QLabel("API Key (Gemini):"))
        row_api.addWidget(self.entry_api)
        config_layout.addLayout(row_api)

        layout.addWidget(config_card)

        # ---- Área de Contexto y Flujo ----
        context_flujo_card = QFrame()
        context_flujo_card.setFrameShape(QFrame.StyledPanel)
        context_flujo_layout = QVBoxLayout(context_flujo_card)

        lbl_context = QLabel("📜 Contexto y Flujo del Proceso")
        lbl_context.setStyleSheet("font-size: 14px; font-weight: bold;")
        context_flujo_layout.addWidget(lbl_context)

        context_flujo_layout.addWidget(QLabel("Contexto General:"))
        self.txt_contexto = QTextEdit()
        self.txt_contexto.setPlaceholderText(
            "Ejemplo: Este requerimiento pertenece al módulo de pagos.\n"
            "El usuario debe poder registrar una transacción y verificarla en el historial."
        )
        self.txt_contexto.setMaximumHeight(80)
        context_flujo_layout.addWidget(self.txt_contexto)

        context_flujo_layout.addWidget(QLabel("Flujo del Proceso:"))
        self.txt_flujo = QTextEdit()
        self.txt_flujo.setPlaceholderText(
            "Ejemplo:\n"
            "1. El usuario ingresa al sistema con sus credenciales. 2. Accede al módulo de facturación. 3. Genera una nueva factura."
        )
        self.txt_flujo.setMaximumHeight(80)
        context_flujo_layout.addWidget(self.txt_flujo)

        layout.addWidget(context_flujo_card)

        # ---- Opciones de pruebas (MEJORADO) ----
        opciones_group = QGroupBox("🧪 Tipos de Pruebas")
        opciones_layout = QVBoxLayout(opciones_group)

        # Checkbox para pruebas funcionales
        self.chk_funcionales = QCheckBox(
            "Pruebas Funcionales: Flujo principal, casos alternativos, validaciones, manejo de errore")
        self.chk_funcionales.setChecked(True)
        opciones_layout.addWidget(self.chk_funcionales)

        # Checkbox para pruebas no funcionales
        self.chk_no_funcionales = QCheckBox(
            "Pruebas No Funcionales: Rendimiento, seguridad, usabilidad, compatibilidad, confiabilidad")
        self.chk_no_funcionales.setChecked(True)
        opciones_layout.addWidget(self.chk_no_funcionales)

        layout.addWidget(opciones_group)

        # ---- Acciones ----
        action_layout = QHBoxLayout()

        self.btn_run = QPushButton("⚡ Generar matrices")
        self.btn_run.clicked.connect(self.ejecutar)
        self.progress = QProgressBar()

        action_layout.addWidget(self.btn_run)
        action_layout.addWidget(self.progress)
        layout.addLayout(action_layout)

        # ---- Resumen ----
        log_card = QFrame()
        log_card.setFrameShape(QFrame.StyledPanel)
        log_layout = QVBoxLayout(log_card)
        lbl_log = QLabel("📜 Resumen de ejecución")
        lbl_log.setStyleSheet("font-size: 14px; font-weight: bold;")
        log_layout.addWidget(lbl_log)

        self.resumen_temp = QPlainTextEdit()
        self.resumen_temp.setReadOnly(True)
        log_layout.addWidget(self.resumen_temp)

        layout.addWidget(log_card)

        # Conectar señales
        signals.progress_max.connect(self.progress.setMaximum)
        signals.progress.connect(self.progress.setValue)
        signals.summary.connect(self.mostrar_resumen)
        signals.info.connect(self.mostrar_info)
        signals.error.connect(self.mostrar_error)
        signals.enable_run.connect(self.toggle_run)

    def seleccionar_in(self):
        d = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if d:
            self.entry_input.setText(d)

    def seleccionar_out(self):
        d = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta")
        if d:
            self.entry_output.setText(d)

    def ejecutar(self):
        input_dir = self.entry_input.text().strip()
        output_dir = self.entry_output.text().strip()
        api_key = self.entry_api.text().strip()
        contexto = self.txt_contexto.toPlainText().strip()
        flujo = self.txt_flujo.toPlainText().strip()

        # Obtener tipos de prueba seleccionados
        tipos_prueba = []
        if self.chk_funcionales.isChecked():
            tipos_prueba.append("funcional")
        if self.chk_no_funcionales.isChecked():
            tipos_prueba.append("no_funcional")

        if not input_dir or not output_dir or not api_key:
            QMessageBox.critical(self, "Error", "Completa todos los campos obligatorios.")
            return

        if not tipos_prueba:
            QMessageBox.critical(self, "Error", "Selecciona al menos un tipo de prueba.")
            return

        # Limpiar resumen anterior
        self.resumen_temp.clear()
        self.progress.setValue(0)

        threading.Thread(
            target=procesar_en_hilo,
            args=(input_dir, output_dir, api_key, contexto, flujo, tipos_prueba),
            daemon=True
        ).start()

    def mostrar_resumen(self, lines):
        self.resumen_temp.clear()
        self.resumen_temp.appendPlainText("\n".join(lines))

    def mostrar_info(self, msg):
        QMessageBox.information(self, "Información", msg)

    def mostrar_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

    def toggle_run(self, enable):
        self.btn_run.setEnabled(enable)
