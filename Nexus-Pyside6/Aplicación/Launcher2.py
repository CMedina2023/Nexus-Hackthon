import sys
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QHBoxLayout, QFrame, QGridLayout,
    QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QLinearGradient, QBrush

# --- Definición de la ruta base del proyecto ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from Migraciotest import GeneradorMatrices
from MigracionStory import GeneradorHistorias
from Chat import JiraAssistantApp


class AnimatedCard(QFrame):
    def __init__(self, name, description, detailed_description, index, icon_name, stacked_widget, is_primary=False):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.index = index
        self.is_primary = is_primary

        # Configuración del frame - tamaño más grande para mejor descripción
        self.setFixedSize(320, 260) 

        self.setObjectName("animated_card")

        # Layout principal con más espacio
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(15)

        # Header con icono y nombre
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)

        # Icono
        icon_label = QLabel()
        icon_size = 38
        icon_path = os.path.join(BASE_DIR, "Icon", icon_name)

        if os.path.exists(icon_path):
            pixmap = QPixmap(icon_path).scaled(
                icon_size, icon_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            icon_label.setPixmap(pixmap)
        else:
            icon_label.setText("🔧")
            icon_label.setStyleSheet(f"font-size: {icon_size - 10}px;")

        icon_label.setFixedSize(icon_size, icon_size)
        header_layout.addWidget(icon_label)

        # Información del título
        title_container = QVBoxLayout()
        title_container.setSpacing(5)

        name_label = QLabel(name)
        name_label.setObjectName("card_title")

        title_container.addWidget(name_label)
        header_layout.addLayout(title_container)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # DESCRIPCIÓN MEJORADA - Sin restricciones de altura
        desc_label = QLabel(description)
        desc_label.setObjectName("card_description")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        # Removemos restricciones de tamaño para que fluya naturalmente
        main_layout.addWidget(desc_label)

        main_layout.addStretch()

        # Botón de acción
        action_btn = QPushButton("Acceder")
        action_btn.setObjectName("card_button")
        action_btn.setEnabled(index > 0)

        if index > 0:
            action_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(index))

        main_layout.addWidget(action_btn)

        # Configurar cursor y hover effect
        if index > 0:
            self.setCursor(Qt.PointingHandCursor)

    def enterEvent(self, event):
        if hasattr(self, 'index') and self.index > 0:
            self.setStyleSheet(self.styleSheet() + """
                QFrame#animated_card {
                    transform: scale(1.02);
                    border: 2px solid #64B5F6;
                }
            """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if hasattr(self, 'index') and self.index > 0:
            self.setStyleSheet(self.styleSheet().replace("""
                QFrame#animated_card {
                    transform: scale(1.02);
                    border: 2px solid #64B5F6;
                }
            """, ""))
        super().leaveEvent(event)


class BenefitsWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("benefits_widget")
        self.setFixedHeight(140)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 25, 40, 25)
        layout.setSpacing(50)

        # Beneficios del conjunto de herramientas
        benefits = [
            ("Mayor Velocidad", "Reduce el tiempo de creación de historias de usuario y casos de prueba hasta en un 80%"),
            ("Consistencia", "Mantiene estándares uniformes en toda la documentación"),
            ("Calidad", "Reduce errores humanos mediante validación automatizada"),
            ("Escalabilidad", "Procesa múltiples documentos simultáneamente")
        ]

        for title, description in benefits:
            benefit_container = QVBoxLayout()
            benefit_container.setSpacing(8)
            benefit_container.setAlignment(Qt.AlignTop)

            # Título del beneficio
            title_label = QLabel(title)
            title_label.setObjectName("benefit_title")

            # Descripción
            desc_label = QLabel(description)
            desc_label.setObjectName("benefit_description")
            desc_label.setWordWrap(True)

            benefit_container.addWidget(title_label)
            benefit_container.addWidget(desc_label)

            # Crear widget contenedor
            benefit_widget = QWidget()
            benefit_widget.setLayout(benefit_container)

            layout.addWidget(benefit_widget)


class MenuPrincipal(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget

        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(30)

        # Header mejorado
        self.setup_header(main_layout)

        # Beneficios
        benefits_widget = BenefitsWidget()
        main_layout.addWidget(benefits_widget)

        # Grid de herramientas rediseñado
        self.setup_tools_grid(main_layout)

        # Spacer
        main_layout.addStretch()

        # Footer mejorado
        self.setup_footer(main_layout)

    def setup_header(self, main_layout):
        header_container = QFrame()
        header_container.setObjectName("header_container")
        header_container.setFixedHeight(100)

        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(30, 20, 30, 20)

        # Lado izquierdo - Logo y título
        left_container = QHBoxLayout()
        left_container.setSpacing(20)

        # Logo más prominente
        logo_label = QLabel()
        logo_path = os.path.join(BASE_DIR, "Icon", "TCS_Logo.png")
        if os.path.exists(logo_path):
            logo_pixmap = QPixmap(logo_path).scaled(
                60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_label.setPixmap(logo_pixmap)
        else:
            logo_label.setText("🏢")
            logo_label.setStyleSheet("font-size: 48px;")

        logo_label.setFixedSize(60, 60)

        # Títulos
        title_container = QVBoxLayout()
        title_container.setSpacing(2)

        main_title = QLabel("Nexus AI")
        main_title.setObjectName("main_title")

        subtitle = QLabel("A smart hub for your test")
        subtitle.setObjectName("main_subtitle")

        title_container.addWidget(main_title)
        title_container.addWidget(subtitle)

        left_container.addWidget(logo_label)
        left_container.addLayout(title_container)
        left_container.addStretch()

        # Lado derecho - Estado del sistema
        right_container = QVBoxLayout()
        right_container.setAlignment(Qt.AlignRight | Qt.AlignCenter)

        status_label = QLabel("🟢 Online")
        status_label.setObjectName("system_status")

        right_container.addWidget(status_label)

        header_layout.addLayout(left_container)
        header_layout.addStretch()
        header_layout.addLayout(right_container)

        main_layout.addWidget(header_container)

    def setup_tools_grid(self, main_layout):
        # Contenedor de herramientas
        tools_container = QFrame()
        tools_container.setObjectName("tools_container")

        tools_layout = QVBoxLayout(tools_container)
        tools_layout.setContentsMargins(20, 30, 20, 30)
        tools_layout.setSpacing(25)

        # Título de sección
        section_title = QLabel("Herramientas Disponibles")
        section_title.setObjectName("section_title")
        tools_layout.addWidget(section_title)

        # Grid layout - tarjetas más grandes para mejores descripciones
        grid_layout = QGridLayout()
        grid_layout.setSpacing(30)
        grid_layout.setAlignment(Qt.AlignCenter)

        # Story Creator con descripción expandida
        story_card = AnimatedCard(
            "Story Creator",
            "Procesamiento inteligente de documentos de requisitos para generar historias de usuario estructuradas con criterios de aceptación automáticos y reglas de negocio detalladas. Transforma documentos complejos en historias claras y accionables siguiendo las mejores prácticas de la industria.",
            "",
            1,
            "story_creator_icon.png",
            self.stacked_widget
        )
        grid_layout.addWidget(story_card, 0, 0)

        # Test Creator con descripción expandida
        test_card = AnimatedCard(
            "Test Creator",
            "Genera matrices de pruebas completas de forma automática a partir de tus documentos de requisitos. Optimiza la cobertura de testing y reduce errores manuales significativamente, creando casos de prueba exhaustivos que cubren todos los escenarios posibles de tu aplicación.",
            "",
            2,
            "test_creator_icon.png",
            self.stacked_widget
        )
        grid_layout.addWidget(test_card, 0, 1)

        # Chat Assistant con descripción expandida
        chat_card = AnimatedCard(
            "Chat Assistant",
            "Consulta especializada para Jira, metodologías ágiles y mejores prácticas de testing. Accede a documentación técnica y guías de configuración con respuestas contextualizadas que te ayudarán a resolver problemas específicos y optimizar tu flujo de trabajo diario.",
            "",
            3,
            "chat_assistant_icon.png",
            self.stacked_widget
        )
        grid_layout.addWidget(chat_card, 0, 2)

        tools_layout.addLayout(grid_layout)
        main_layout.addWidget(tools_container)

    def setup_footer(self, main_layout):
        footer_container = QFrame()
        footer_container.setObjectName("footer_container")
        footer_container.setFixedHeight(60)

        footer_layout = QHBoxLayout(footer_container)
        footer_layout.setContentsMargins(30, 15, 30, 15)

        # Información del desarrollador
        dev_info = QHBoxLayout()
        dev_info.setSpacing(10)

        dev_icon = QLabel("👨‍💻")
        dev_icon.setStyleSheet("font-size: 20px;")

        dev_label = QLabel("Desarrollado por Carlos Medina")
        dev_label.setObjectName("dev_info")

        version_label = QLabel("v2.0")
        version_label.setObjectName("version_info")

        dev_info.addWidget(dev_icon)
        dev_info.addWidget(dev_label)
        dev_info.addWidget(version_label)
        dev_info.addStretch()

        # Botón de salida mejorado
        exit_button = QPushButton("Salir")
        exit_button.setObjectName("exit_button")
        exit_button.setFixedSize(100, 35)
        exit_button.clicked.connect(QApplication.instance().quit)

        footer_layout.addLayout(dev_info)
        footer_layout.addStretch()
        footer_layout.addWidget(exit_button)

        main_layout.addWidget(footer_container)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Nexus AI: A smart hub for your test")
        self.setMinimumSize(1200, 800)

        # Estilos modernos y profesionales - SIN SOMBRAS
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #0F0F23, stop: 1 #1A1A2E);
                color: #FFFFFF;
                font-family: 'Segoe UI', 'Arial', sans-serif;
            }

            /* Header */
            #header_container {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #16213E, stop: 1 #0F3460);
                border-radius: 15px;
                border: 1px solid #1E3A8A;
            }

            #main_title {
                font-size: 32px;
                font-weight: bold;
                color: #60A5FA;
                background: transparent;
                border: none;
            }

            #main_subtitle {
                font-size: 16px;
                color: #94A3B8;
                font-weight: 400;
            }

            #system_status {
                font-size: 14px;
                color: #10B981;
                font-weight: 500;
            }

            /* Benefits Widget */
            #benefits_widget {
                background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #1E293B, stop: 1 #334155);
                border-radius: 15px;
                border: 1px solid #374151;
            }

            #benefit_title {
                font-size: 18px;
                font-weight: bold;
                color: #10B981;
                margin-bottom: 5px;
            }

            #benefit_description {
                font-size: 13px;
                color: #CBD5E0;
                line-height: 1.4;
            }

            /* Tools Container */
            #tools_container {
                background: rgba(30, 41, 59, 0.6);
                border-radius: 20px;
                border: 1px solid #334155;
            }

            #section_title {
                font-size: 24px;
                font-weight: bold;
                color: #E2E8F0;
                margin-bottom: 10px;
            }

            /* Animated Cards - SIN SOMBRAS */
            #animated_card {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2D3748, stop: 1 #1A202C);
                border-radius: 16px;
                border: 1px solid #4A5568;
                transition: all 0.3s ease;
                /* ELIMINAMOS todas las sombras */
            }

            #animated_card:hover {
                transform: translateY(-5px);
                border: 2px solid #3B82F6;
                /* NO agregamos box-shadow aquí */
            }

            #card_title {
                font-size: 20px;
                font-weight: bold;
                color: #F7FAFC;
                margin-bottom: 8px;
            }

            /* DESCRIPCIÓN MEJORADA - SIN FONDO OSCURO */
            #card_description {
                font-size: 14px;
                color: #CBD5E0;
                line-height: 1.6;
                margin: 10px 0 15px 0;
                padding: 5px 0;
                text-align: justify;
                background: transparent;
                /* Fondo completamente transparente */
                border: none;
                /* Sin bordes */
            }

            #card_subtitle {
                font-size: 14px;
                color: #A0AEC0;
                line-height: 1.4;
            }

            #card_detail {
                font-size: 13px;
                color: #CBD5E0;
                line-height: 1.5;
                margin: 10px 0;
            }

            /* Buttons */
            #card_button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #059669, stop: 1 #047857);
                color: white;
                border: 2px solid white;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 500;
            }

            #card_button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #10B981, stop: 1 #059669);
                border: 2px solid white;
            }

            #card_button:disabled {
                background: #4B5563;
                color: #9CA3AF;
                border: 2px solid #6B7280;
            }

            /* Footer */
            #footer_container {
                background: rgba(15, 23, 42, 0.8);
                border-radius: 10px;
                border-top: 1px solid #334155;
            }

            #dev_info {
                color: #94A3B8;
                font-size: 14px;
            }

            #version_info {
                background: #1E40AF;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: bold;
            }

            #exit_button {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #DC2626, stop: 1 #B91C1C);
                color: white;
                border: 2px solid white;
                border-radius: 8px;
                font-weight: 600;
            }

            #exit_button:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #EF4444, stop: 1 #DC2626);
                border: 2px solid white;
            }
        """)

        # Configurar el stacked widget
        self.stacked_widget = QStackedWidget(self)

        # Crear las pantallas
        self.menu = MenuPrincipal(self.stacked_widget)
        self.stacked_widget.addWidget(self.menu)

        self.gen_story = GeneradorHistorias(self.stacked_widget)
        self.stacked_widget.addWidget(self.gen_story)

        self.gen_test = GeneradorMatrices(self.stacked_widget)
        self.stacked_widget.addWidget(self.gen_test)

        self.chat_app = JiraAssistantApp(self.stacked_widget)
        self.stacked_widget.addWidget(self.chat_app)

        # Layout principal
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stacked_widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

