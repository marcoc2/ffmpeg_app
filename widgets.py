from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QCheckBox
)

class ConcatOptionsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Resolução:"))
        self.res_heuristic_combo = QComboBox()
        self.res_heuristic_combo.addItems([
            "Maior Duração Total",
            "Maior Resolução",
            "Maioria (Contagem)",
            "Primeiro Arquivo",
            "Manual",
        ])
        self.res_heuristic_combo.setMinimumWidth(180)
        row1.addWidget(self.res_heuristic_combo)

        row1.addSpacing(15)
        row1.addWidget(QLabel("Ajuste:"))
        self.crop_combo = QComboBox()
        self.crop_combo.addItems([
            "Letterbox (Barras Pretas)",
            "Crop Centro",
            "Crop Cima",
            "Crop Baixo",
            "Crop Esquerda",
            "Crop Direita",
        ])
        self.crop_combo.setMinimumWidth(180)
        row1.addWidget(self.crop_combo)
        row1.addStretch()
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        self.manual_lbl = QLabel("Largura:")
        row2.addWidget(self.manual_lbl)
        self.manual_w_spin = QSpinBox()
        self.manual_w_spin.setRange(2, 7680)
        self.manual_w_spin.setValue(1920)
        self.manual_w_spin.setSingleStep(2)
        self.manual_w_spin.setFixedWidth(80)
        row2.addWidget(self.manual_w_spin)
        self.manual_h_lbl = QLabel("Altura:")
        row2.addWidget(self.manual_h_lbl)
        self.manual_h_spin = QSpinBox()
        self.manual_h_spin.setRange(2, 4320)
        self.manual_h_spin.setValue(1080)
        self.manual_h_spin.setSingleStep(2)
        self.manual_h_spin.setFixedWidth(80)
        row2.addWidget(self.manual_h_spin)
        row2.addStretch()
        layout.addLayout(row2)

        self.res_heuristic_combo.currentTextChanged.connect(self._on_heuristic_changed)
        self._on_heuristic_changed(self.res_heuristic_combo.currentText())

    def _on_heuristic_changed(self, text):
        is_manual = text == "Manual"
        self.manual_lbl.setVisible(is_manual)
        self.manual_w_spin.setVisible(is_manual)
        self.manual_h_lbl.setVisible(is_manual)
        self.manual_h_spin.setVisible(is_manual)

class SpatialCropWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("W:"))
        self.sc_w_spin = QSpinBox()
        self.sc_w_spin.setRange(2, 7680)
        self.sc_w_spin.setValue(480)
        self.sc_w_spin.setSingleStep(2)
        self.sc_w_spin.setFixedWidth(70)
        layout.addWidget(self.sc_w_spin)

        layout.addWidget(QLabel("H:"))
        self.sc_h_spin = QSpinBox()
        self.sc_h_spin.setRange(2, 4320)
        self.sc_h_spin.setValue(480)
        self.sc_h_spin.setSingleStep(2)
        self.sc_h_spin.setFixedWidth(70)
        layout.addWidget(self.sc_h_spin)

        layout.addSpacing(10)

        self.sc_center_cb = QCheckBox("Centro")
        self.sc_center_cb.setChecked(True)
        self.sc_center_cb.toggled.connect(self._on_sc_center_toggled)
        layout.addWidget(self.sc_center_cb)

        layout.addSpacing(10)

        self.sc_x_lbl = QLabel("X:")
        layout.addWidget(self.sc_x_lbl)
        self.sc_x_spin = QSpinBox()
        self.sc_x_spin.setRange(0, 7680)
        self.sc_x_spin.setValue(0)
        self.sc_x_spin.setFixedWidth(70)
        self.sc_x_spin.setEnabled(False)
        layout.addWidget(self.sc_x_spin)

        self.sc_y_lbl = QLabel("Y:")
        layout.addWidget(self.sc_y_lbl)
        self.sc_y_spin = QSpinBox()
        self.sc_y_spin.setRange(0, 4320)
        self.sc_y_spin.setValue(0)
        self.sc_y_spin.setFixedWidth(70)
        self.sc_y_spin.setEnabled(False)
        layout.addWidget(self.sc_y_spin)

        layout.addStretch()

    def _on_sc_center_toggled(self, checked):
        self.sc_x_spin.setEnabled(not checked)
        self.sc_y_spin.setEnabled(not checked)

class MemoryFlashOptionsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Fragmentos:"))
        self.flash_count_spin = QSpinBox()
        self.flash_count_spin.setRange(1, 50)
        self.flash_count_spin.setValue(4)
        self.flash_count_spin.setFixedWidth(50)
        row1.addWidget(self.flash_count_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Subfragmentos:"))
        self.flash_sub_spin = QSpinBox()
        self.flash_sub_spin.setRange(1, 30)
        self.flash_sub_spin.setValue(3)
        self.flash_sub_spin.setFixedWidth(50)
        row1.addWidget(self.flash_sub_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Tamanho (frames):"))
        self.flash_size_spin = QSpinBox()
        self.flash_size_spin.setRange(1, 60)
        self.flash_size_spin.setValue(2)
        self.flash_size_spin.setFixedWidth(50)
        row1.addWidget(self.flash_size_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Espaçamento (frames):"))
        self.flash_gap_spin = QSpinBox()
        self.flash_gap_spin.setRange(1, 300)
        self.flash_gap_spin.setValue(3)
        self.flash_gap_spin.setFixedWidth(60)
        row1.addWidget(self.flash_gap_spin)

        row1.addSpacing(10)
        row1.addWidget(QLabel("Seed:"))
        self.flash_seed_spin = QSpinBox()
        self.flash_seed_spin.setRange(0, 999999)
        self.flash_seed_spin.setValue(0)
        self.flash_seed_spin.setFixedWidth(70)
        row1.addWidget(self.flash_seed_spin)

        row1.addStretch()
        layout.addLayout(row1)
