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
    QHBoxLayout, QFrame, QPlainTextEdit, QStackedWidget
)
from PySide6.QtCore import Signal, QObject, Qt, QThread  # QThread es necesario para la clase
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
def listar_archivos(carpeta, incluir_subcarpetas=False):
    exts = (".docx", ".pdf")
    archivos = []
    if incluir_subcarpetas:
        for root, _, files in os.walk(carpeta):
            for f in files:
                if f.lower().endswith(exts):
                    archivos.append(os.path.join(root, f))
    else:
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
# IA (Gemini)
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


def generar_casos_gemini(api_key, requerimiento, contexto_general, flujo_proceso):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = (
            "Eres un experto en QA. Devuelve SOLO un array JSON de objetos con claves:\n"
            ' - "Nombre"\n - "Descripcion"\n - "Pasos" (array)\n'
            ' - "Resultado esperado"\n - "Prioridad"\n\n'
            f"Contexto: {contexto_general}\nFlujo: {flujo_proceso}\n\nRequerimiento:\n{requerimiento}"
        )
        response = model.generate_content(prompt)
        texto = getattr(response, "text", "") or ""
        return _extraer_json_array(texto)
    except Exception:
        return []


# ----------------------------
# Guardado CSV
# ----------------------------
def guardar_csv(casos, output_path):
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Nombre de caso de prueba", "Descripcion", "Pasos",
                "Resultado esperado", "Prioridad"
            ])
            for c in casos:
                writer.writerow([
                    c.get("Nombre", ""),
                    c.get("Descripcion", ""),
                    " | ".join(c.get("Pasos", []) or []),
                    c.get("Resultado esperado", ""),
                    c.get("Prioridad", ""),
                ])
        return True
    except Exception:
        return False


# ----------------------------
# Proceso en hilo
# ----------------------------
def procesar_en_hilo(input_dir, output_dir, api_key, contexto, flujo, incluir_sub):
    archivos = listar_archivos(input_dir, incluir_subcarpetas=incluir_sub)
    if not archivos:
        signals.info.emit("No se encontraron .docx/.pdf en la carpeta seleccionada.")
        return

    total = len(archivos)
    signals.progress_max.emit(total)
    signals.progress.emit(0)
    signals.enable_run.emit(False)

    resumen = []

    for i, path in enumerate(archivos, start=1):
        nombre = os.path.basename(path)
        texto = leer_requerimiento(path)
        if not texto:
            resumen.append(f"{nombre} → 0 casos")
            signals.progress.emit(i)
            continue

        casos = generar_casos_gemini(api_key, texto, contexto, flujo) or []
        conteo = len(casos)
        nombre_base = os.path.splitext(nombre)[0]
        out_path = os.path.join(output_dir, f"{nombre_base}_matriz.csv")
        if conteo > 0:
            guardar_csv(casos, out_path)
        resumen.append(f"{nombre} → {conteo} casos")

        signals.progress.emit(i)

    signals.summary.emit(resumen)
    signals.enable_run.emit(True)
    signals.info.emit("Proceso completado.")


# ----------------------------
# UI principal como QWidget
# ----------------------------
class GeneradorMatrices(QWidget):
    # El constructor ahora acepta un stacked_widget
    def __init__(self, stacked_widget):
        super().__init__()
        self.setWindowTitle("Generador de Matrices de Pruebas (IA)")
        self.resize(900, 750)
        self.stacked_widget = stacked_widget  # Guarda la referencia al stacked widget

        # --- Estilos Locales ---
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2F;
                color: #F5F5F5;
                font-family: 'Segoe UI';
                font-size: 14px;
            }
            QFrame {
                background-color: #2A2A40;
                border-radius: 12px;
                border: 1px solid #3C3C5C;
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
        self.entry_input.setPlaceholderText(
            "Da click en el botón 'seleccionar' para colocar la ruta\n"
        )
        btn_in = QPushButton("Seleccionar")
        btn_in.clicked.connect(self.seleccionar_in)
        row_in.addWidget(QLabel("Carpeta de Requerimientos:"))
        row_in.addWidget(self.entry_input)
        row_in.addWidget(btn_in)
        config_layout.addLayout(row_in)

        # Carpeta salida
        row_out = QHBoxLayout()
        self.entry_output = QLineEdit()
        self.entry_output.setPlaceholderText(
            "Da click en el botón 'seleccionar' para colocar la ruta\n"
        )
        btn_out = QPushButton("Seleccionar")
        btn_out.clicked.connect(self.seleccionar_out)
        row_out.addWidget(QLabel("Carpeta de Salida:"))
        row_out.addWidget(self.entry_output)
        row_out.addWidget(btn_out)
        config_layout.addLayout(row_out)

        # API Key
        row_api = QHBoxLayout()
        self.entry_api = QLineEdit()
        self.entry_api.setPlaceholderText(
            "Ejemplo: AIzaSyD3x-xxxx-xxxx-xxxx-xxxxx\n"
        )
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
        context_flujo_layout.addWidget(self.txt_contexto)

        context_flujo_layout.addWidget(QLabel("Flujo del Proceso:"))
        self.txt_flujo = QTextEdit()
        self.txt_flujo.setPlaceholderText(
            "Ejemplo:\n"
            "1. El usuario ingresa al sistema con sus credenciales.\n"
            "2. Accede al módulo de facturación..\n"
            "3. Genera una nueva factura.\n"
        )
        context_flujo_layout.addWidget(self.txt_flujo)

        layout.addWidget(context_flujo_card)

        # ---- Acciones ----
        action_layout = QHBoxLayout()
        self.chk_subcarpetas = QCheckBox("Incluir subcarpetas")
        action_layout.addWidget(self.chk_subcarpetas)

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
        incluir_sub = self.chk_subcarpetas.isChecked()

        if not input_dir or not output_dir or not api_key:
            QMessageBox.critical(self, "Error", "Completa todos los campos.")
            return

        threading.Thread(
            target=procesar_en_hilo,
            args=(input_dir, output_dir, api_key, contexto, flujo, incluir_sub),
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