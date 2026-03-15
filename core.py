import sys
import os
import subprocess
import traceback
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal

def exception_hook(exctype, value, tb):
    """Global exception hook to capture crashes that don't reach the console."""
    err_msg = "".join(traceback.format_exception(exctype, value, tb))
    print(err_msg, file=sys.stderr)
    try:
        with open("crash_report.txt", "a", encoding="utf-8") as f:
            f.write(f"\n--- CRASH AT {datetime.now()} ---\n")
            f.write(err_msg)
            f.write("-" * 30 + "\n")
    except Exception:
        pass
    sys.__excepthook__(exctype, value, tb)

class FFmpegWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def __init__(self, command, cwd):
        super().__init__()
        self.command = command
        self.cwd = cwd

    def run(self):
        try:
            process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )

            for line in process.stdout:
                self.output_signal.emit(line.strip())

            process.wait()
            self.finished_signal.emit(process.returncode)
        except Exception as e:
            self.output_signal.emit(f"Error executing command: {str(e)}")
            self.finished_signal.emit(-1)

OPERATIONS = {
    "Concatenar Videos": "concat",
    "Extrair Audio (MP3)": "extract_audio",
    "Converter para MP4 (H.264)": "to_mp4",
    "Converter para GIF": "to_gif",
    "Redimensionar (720p)": "scale_720p",
    "Remover Audio (Mute)": "mute",
    "Mix de Audio": "mix_audio",
    "Substituir Audio de Video": "replace_audio",
    "Cortar Início (Frames)": "cut_front",
    "Cortar Fim (Frames)": "cut_back",
    "Loop Final (Frames)": "loop_end",
    "Loop Final (Ping-Pong)": "loop_pingpong",
    "Imagem para Vídeo": "image_to_video",
    "Crop Espacial": "spatial_crop",
    "Flash de Memória": "memory_flash",
    "Lado a Lado (Side-by-Side)": "side_by_side",
    "Marca d'água / Overlay": "overlay",
}
