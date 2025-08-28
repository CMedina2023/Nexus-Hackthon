import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QHBoxLayout, QFrame, QGridLayout,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap

# --- Definición de la ruta base del proyecto ---
# Esto asegura que la ruta funcione sin importar dónde se ejecute el script
# y asume que la carpeta 'Icon' está en el mismo directorio que Launcher2.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


from Migraciotest import GeneradorMatrices
from MigracionStory import GeneradorHistorias
from Chat import JiraAssistantApp


class MenuPrincipal(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(50, 50, 50, 50)

        # ---- Sección Superior: Título y Logo ----
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setSpacing(20)

        # Contenedor para el mensaje y el título
        title_container_layout = QVBoxLayout()
        title_container_layout.setSpacing(5)  # Espacio entre los dos labels

        welcome_label = QLabel("<h1>Bienvenido a:</h1>")
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("color: #F5F5F5;")

        title_label = QLabel("<h2>Nexus AI - A smart hub for your test</h2>")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #F5F5F5;")

        title_container_layout.addWidget(welcome_label)
        title_container_layout.addWidget(title_label)

        # Agrega el contenedor al layout principal de la barra superior
        top_bar_layout.addStretch()
        top_bar_layout.addLayout(title_container_layout)  # Agregamos el layout que contiene los dos QLabel
        top_bar_layout.addStretch()

        # Logo
        logo_placeholder = QLabel()
        logo_path = os.path.join(BASE_DIR, "Icon", "TCS_Logo.png")
        logo_pixmap = QPixmap(logo_path).scaled(80, 80,
                                                Qt.KeepAspectRatio,
                                                Qt.SmoothTransformation)
        logo_placeholder.setPixmap(logo_pixmap)
        logo_placeholder.setFixedSize(80, 80)
        logo_placeholder.setAlignment(Qt.AlignCenter)
        top_bar_layout.addWidget(logo_placeholder, alignment=Qt.AlignRight | Qt.AlignTop)

        main_layout.addLayout(top_bar_layout)
        main_layout.addSpacing(40)

        # ---- Grid de Tarjetas ----
        grid_layout = QGridLayout()
        grid_layout.setSpacing(30)

        # --- Función auxiliar para crear tarjetas ---
        def create_card(name, description, index, icon_name):
            card = QFrame()
            card.setFixedSize(300, 200)
            card.setObjectName("tool_card")

            vbox = QVBoxLayout(card)
            vbox.setAlignment(Qt.AlignCenter)
            vbox.setSpacing(10)

            # Contenedor para el icono y el nombre (HORIZONTAL)
            icon_name_layout = QHBoxLayout()
            icon_name_layout.setSpacing(10)
            icon_name_layout.setAlignment(Qt.AlignCenter)

            # Icono
            icon_label = QLabel()
            icon_label.setObjectName("tool_icon")

            # Carga y escala el ícono
            icon_path = os.path.join(BASE_DIR, "Icon", icon_name)
            if os.path.exists(icon_path):
                pixmap = QPixmap(icon_path).scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(pixmap)
            else:
                icon_label.setText("Ícono")
                icon_label.setStyleSheet("border: 1px dashed #666; color: #AAAAAA; border-radius: 8px;")

            icon_label.setFixedSize(38, 38)
            icon_name_layout.addWidget(icon_label)

            # Nombre de la herramienta
            name_label = QLabel(name)
            name_label.setObjectName("tool_name")
            icon_name_layout.addWidget(name_label)

            vbox.addLayout(icon_name_layout)

            # Descripción
            desc_label = QLabel(description)
            desc_label.setObjectName("tool_desc")
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setWordWrap(True)
            vbox.addWidget(desc_label)

            # Botón
            btn = QPushButton("Acceder")
            btn.setObjectName("tool_button")
            btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(index))
            vbox.addWidget(btn)

            return card

        # Añadir tarjetas al grid
        grid_layout.addWidget(
            create_card(
                "Story Creator",
                "Genera historias de usuario y requisitos funcionales y no funcionales.",
                1,
                "story_creator_icon.png"
            ), 0, 0)
        grid_layout.addWidget(
            create_card(
                "Test Creator",
                "Crea matrices de trazabilidad y casos de prueba automáticamente.",
                2,
                "test_creator_icon.png"
            ), 0, 1)
        grid_layout.addWidget(
            create_card(
                "Chat Assistant",
                "Asistente inteligente de QA y Jira para consultas rápidas.",
                3,
                "chat_assistant_icon.png"
            ), 1, 0)
        grid_layout.addWidget(
            create_card(
                "Próxima Herramienta",
                "Próximamente una nueva funcionalidad de IA.",
                0,
                "proxima_herramienta_icon.png"
            ), 1, 1)

        main_layout.addLayout(grid_layout)
        main_layout.addStretch()

        # ---- Pie de página ----
        footer_layout = QHBoxLayout()

        dev_label = QLabel("Desarrollado por Carlos Medina")
        dev_label.setStyleSheet("color: #AAAAAA;")
        footer_layout.addWidget(dev_label)
        footer_layout.addStretch()

        exit_button = QPushButton("Salir")
        exit_button.setFixedSize(80, 40)
        exit_button.setStyleSheet("""
            QPushButton {
                background-color: #D32F2F;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                border: 1px solid white;
            }
            QPushButton:hover {
                background-color: #E57373;
            }
        """)
        exit_button.clicked.connect(QApplication.instance().quit)
        footer_layout.addWidget(exit_button, alignment=Qt.AlignBottom | Qt.AlignRight)

        main_layout.addLayout(footer_layout)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nexus AI: A smart hub for your test")
        self.setMinimumSize(1000, 750)

        # 🎨 Estilos globales
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E2F;
                color: #F5F5F5;
                font-family: 'Segoe UI';
            }
            #tool_card {
                background-color: #2A2A40;
                border-radius: 16px;
                border: 1px solid #3C3C5C;
                padding: 15px;
            }
            #tool_name {
                font-size: 18px;
                font-weight: bold;
                color: #B0C4DE;
            }
            #tool_icon {
                background-color: #3A3A50;
                border: 1px dashed #666;
                color: #AAAAAA;
                border-radius: 8px;
            }
            #tool_desc {
                font-size: 14px;
                color: #CCCCCC;
                background-color: transparent;
            }
            #tool_button {
                background-color: #3F51B5;
                color: white;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                border: 1px solid white;
            }
            #tool_button:hover {
                background-color: #5C6BC0;
            }
            QLabel {
                font-size: 14px;
            }
        """)

        self.stacked_widget = QStackedWidget(self)

        self.menu = MenuPrincipal(self.stacked_widget)
        self.stacked_widget.addWidget(self.menu)

        self.gen_story = GeneradorHistorias(self.stacked_widget)
        self.stacked_widget.addWidget(self.gen_story)

        self.gen_test = GeneradorMatrices(self.stacked_widget)
        self.stacked_widget.addWidget(self.gen_test)

        self.chat_app = JiraAssistantApp(self.stacked_widget)
        self.stacked_widget.addWidget(self.chat_app)

        layout = QVBoxLayout(self)
        layout.addWidget(self.stacked_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())