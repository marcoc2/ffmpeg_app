import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QListWidget, QAbstractItemView, QListWidgetItem, 
    QLabel, QMessageBox, QTextEdit, QComboBox, QFileDialog, QSpinBox
)
from PyQt6.QtCore import Qt

# Import modular components
from core import FFmpegWorker, OPERATIONS, exception_hook
from widgets import ConcatOptionsWidget, SpatialCropWidget, MemoryFlashOptionsWidget, GhostImagesOptionsWidget
import ffmpeg_logic

sys.excepthook = exception_hook

if sys.platform == "win32":
    import ctypes
    myappid = "marcoc2.ffmpegtools.v1"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

class FFmpegApp(QMainWindow):
    def __init__(self, initial_operation=None, initial_files=None):
        super().__init__()
        self.setWindowTitle("FFmpeg Tools")
        self.resize(650, 500)
        self.file_metadata = {}

        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg_tools.ico")
        if os.path.exists(icon_path):
            from PyQt6.QtGui import QIcon
            self.setWindowIcon(QIcon(icon_path))

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        # UI Setup
        self._setup_top_ui()
        self._setup_list_ui()
        self._setup_options_widgets()
        self._setup_bottom_ui()

        if initial_files:
            for f in initial_files: self.add_file(os.path.abspath(f))
        if initial_operation:
            for k, v in OPERATIONS.items():
                if v == initial_operation:
                    self.op_combo.setCurrentText(k)
                    break
        self._on_operation_changed(self.op_combo.currentText())

    def _setup_top_ui(self):
        op_layout = QHBoxLayout()
        op_layout.addWidget(QLabel("Operação:"))
        self.op_combo = QComboBox()
        self.op_combo.addItems(OPERATIONS.keys())
        self.op_combo.setMinimumWidth(250)
        op_layout.addWidget(self.op_combo)
        op_layout.addSpacing(20)

        self.frames_lbl_title = QLabel("Frames:")
        op_layout.addWidget(self.frames_lbl_title)
        self.frames_spin = QSpinBox()
        self.frames_spin.setRange(1, 999999)
        self.frames_spin.setValue(30)
        self.frames_spin.setFixedWidth(80)
        op_layout.addWidget(self.frames_spin)

        self.loop_lbl_title = QLabel("Vezes (Loop):")
        op_layout.addWidget(self.loop_lbl_title)
        self.loop_spin = QSpinBox()
        self.loop_spin.setRange(1, 999)
        self.loop_spin.setValue(3)
        self.loop_spin.setFixedWidth(50)
        op_layout.addWidget(self.loop_spin)

        self.fps_lbl_title = QLabel("FPS:")
        op_layout.addWidget(self.fps_lbl_title)
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(30)
        self.fps_spin.setFixedWidth(50)
        op_layout.addWidget(self.fps_spin)

        op_layout.addStretch()
        self.main_layout.addLayout(op_layout)
        self.op_combo.currentTextChanged.connect(self._on_operation_changed)

    def _setup_list_ui(self):
        self.info_label = QLabel("Nenhum vídeo carregado.")
        self.info_label.setStyleSheet("color: #666; font-size: 11px;")
        self.main_layout.addWidget(self.info_label)

        self.main_layout.addWidget(QLabel("Arraste e solte arquivos aqui:"))
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setAcceptDrops(True)
        # Custom drag drop handlers as before
        self.list_widget.dragEnterEvent = self._dragEnterEvent
        self.list_widget.dragMoveEvent = self._dragMoveEvent
        self.list_widget.dropEvent = self._dropEvent
        self.main_layout.addWidget(self.list_widget)

        self.compat_label = QLabel("")
        self.compat_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        self.compat_label.setWordWrap(True)
        self.main_layout.addWidget(self.compat_label)

    def _setup_options_widgets(self):
        self.concat_opts = ConcatOptionsWidget()
        self.spatial_crop_opts = SpatialCropWidget()
        self.flash_opts = MemoryFlashOptionsWidget()
        self.ghost_opts = GhostImagesOptionsWidget()
        
        for w in [self.concat_opts, self.spatial_crop_opts, self.flash_opts, self.ghost_opts]:
            w.setVisible(False)
            self.main_layout.addWidget(w)

    def _setup_bottom_ui(self):
        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Adicionar Arquivos")
        self.btn_add.clicked.connect(self.add_files_dialog)
        
        self.btn_up = QPushButton("▲")
        self.btn_up.setFixedWidth(32)
        self.btn_up.clicked.connect(self.move_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setFixedWidth(32)
        self.btn_down.clicked.connect(self.move_down)

        self.btn_remove = QPushButton("Remover")
        self.btn_remove.clicked.connect(self.remove_selected)

        self.btn_run = QPushButton("▶  Executar FFmpeg")
        self.btn_run.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white; padding: 6px 16px;")
        self.btn_run.clicked.connect(self.run_ffmpeg)

        for b in [self.btn_add, self.btn_up, self.btn_down, self.btn_remove]: btn_layout.addWidget(b)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_run)
        self.main_layout.addLayout(btn_layout)

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.hide()
        self.main_layout.addWidget(self.log_console)

    def _on_operation_changed(self, text):
        op = OPERATIONS.get(text, "")
        self.frames_lbl_title.setVisible(op in ("cut_front", "cut_back", "loop_end", "loop_pingpong", "image_to_video"))
        self.frames_spin.setVisible(self.frames_lbl_title.isVisible())
        self.loop_lbl_title.setVisible(op in ("loop_end", "loop_pingpong"))
        self.loop_spin.setVisible(self.loop_lbl_title.isVisible())
        self.fps_lbl_title.setVisible(op == "image_to_video")
        self.fps_spin.setVisible(self.fps_lbl_title.isVisible())

        self.spatial_crop_opts.setVisible(op in ("spatial_crop", "overlay"))
        self.flash_opts.setVisible(op == "memory_flash")
        self.ghost_opts.setVisible(op == "ghost_images")
        self.analyze_compatibility()

    def analyze_compatibility(self):
        if self.list_widget.count() < 1:
            self.compat_label.setText(""); self.concat_opts.setVisible(False); return
        op = OPERATIONS.get(self.op_combo.currentText())
        if op != "concat":
            self.compat_label.setText(""); self.concat_opts.setVisible(False); return
        
        first = self.list_widget.item(0).data(Qt.ItemDataRole.UserRole)
        meta = self.file_metadata.get(first)
        if not meta or not meta.get("is_video"):
            self.compat_label.setText("⚠ Inválido"); self.concat_opts.setVisible(False); return

        issues = []
        for i in range(self.list_widget.count()):
            path = self.list_widget.item(i).data(Qt.ItemDataRole.UserRole)
            m = self.file_metadata.get(path)
            if not m: continue
            self.list_widget.item(i).setText(f"{os.path.basename(path)} - ({m['width']}x{m['height']}, {m['fps']} FPS)")
            if i > 0 and (m['width'] != meta['width'] or m['height'] != meta['height'] or abs(m['fps'] - meta['fps']) > 0.01):
                issues.append(f"Item {i+1}")
        
        if issues:
            self.compat_label.setText(f"⚠ Incompatível: {', '.join(issues[:2])}"); self.compat_label.setStyleSheet("color: red")
            self.concat_opts.setVisible(True)
        else:
            self.compat_label.setText("✅ Compatível"); self.compat_label.setStyleSheet("color: green")
            self.concat_opts.setVisible(False)

    def add_file(self, path):
        for i in range(self.list_widget.count()):
            if self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) == path: return
        item = QListWidgetItem(os.path.basename(path))
        item.setData(Qt.ItemDataRole.UserRole, path)
        self.list_widget.addItem(item)
        if path not in self.file_metadata:
            meta = ffmpeg_logic.get_video_info(path)
            if meta: self.file_metadata[path] = meta
        self.analyze_compatibility()

    def add_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Selecionar", "", "Videos (*.mp4 *.mkv *.avi *.gif);;Todos (*)")
        for f in files: self.add_file(f)

    def move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row-1, item)
            self.list_widget.setCurrentRow(row-1); self.analyze_compatibility()

    def move_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count()-1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row+1, item)
            self.list_widget.setCurrentRow(row+1); self.analyze_compatibility()

    def remove_selected(self):
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self.analyze_compatibility()

    def run_ffmpeg(self):
        if self.list_widget.count() == 0: return
        files = [self.list_widget.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list_widget.count())]
        op = OPERATIONS[self.op_combo.currentText()]
        config = {
            "frames": self.frames_spin.value(), "loops": self.loop_spin.value(), "fps": self.fps_spin.value(),
            "res_heuristic": self.concat_opts.res_heuristic_combo.currentText(),
            "crop_mode": self.concat_opts.crop_combo.currentText(),
            "manual_w": self.concat_opts.manual_w_spin.value(), "manual_h": self.concat_opts.manual_h_spin.value(),
            "sc_w": self.spatial_crop_opts.sc_w_spin.value(), "sc_h": self.spatial_crop_opts.sc_h_spin.value(),
            "sc_center": self.spatial_crop_opts.sc_center_cb.isChecked(),
            "sc_x": self.spatial_crop_opts.sc_x_spin.value(), "sc_y": self.spatial_crop_opts.sc_y_spin.value(),
            "flash_count": self.flash_opts.flash_count_spin.value(), "flash_sub": self.flash_opts.flash_sub_spin.value(),
            "flash_size": self.flash_opts.flash_size_spin.value(), "flash_gap": self.flash_opts.flash_gap_spin.value(),
            "seed": self.flash_opts.flash_seed_spin.value(),
            "ghost_start": self.ghost_opts.ghost_start_spin.value(), "ghost_end": self.ghost_opts.ghost_end_spin.value(),
            "ghost_dur": self.ghost_opts.ghost_dur_spin.value(), "ghost_opacity": self.ghost_opts.ghost_opacity_spin.value()
        }
        
        cmd, out, err = ffmpeg_logic.build_command(op, files, config, self.file_metadata)
        if err:
            QMessageBox.warning(self, "Erro", err); return
        if not cmd: return

        self.btn_run.setEnabled(False); self.log_console.clear(); self.log_console.show()
        self.log(f"Executando:\n{' '.join(cmd)}\n")
        self.worker = FFmpegWorker(cmd, os.path.dirname(files[0]))
        self.worker.output_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_process_finished)
        self.worker.start()

    def log(self, text):
        self.log_console.append(text)
        self.log_console.verticalScrollBar().setValue(self.log_console.verticalScrollBar().maximum())

    def on_process_finished(self, code):
        self.btn_run.setEnabled(True)
        self.log("\n--- SUCESSO ---" if code == 0 else f"\n--- FALHOU ({code}) ---")
        if code == 0 and OPERATIONS[self.op_combo.currentText()] == "concat":
            try: os.remove(os.path.join(os.path.dirname(self.list_widget.item(0).data(Qt.ItemDataRole.UserRole)), "concat.txt"))
            except: pass

    def _dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()
    def _dragMoveEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()
    def _dropEvent(self, e):
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                if url.isLocalFile(): self.add_file(url.toLocalFile())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    op = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in OPERATIONS.values() else None
    files = sys.argv[2:] if op else sys.argv[1:]
    window = FFmpegApp(initial_operation=op, initial_files=files)
    window.show()
    sys.exit(app.exec())
