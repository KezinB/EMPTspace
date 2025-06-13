import sys
import re
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QTextEdit, QFileDialog, QComboBox
)
from PyQt5.QtGui import QTextCursor, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class GCodeLoader(QThread):
    loaded = pyqtSignal(str)

    def __init__(self, filename):
        super().__init__()
        self.filename = filename

    def run(self):
        with open(self.filename, 'r', encoding='utf-8', errors='ignore') as f:
            gcode = f.read()
        self.loaded.emit(gcode)

class GCodeViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G-code Resume Helper")
        self.resize(900, 600)
        self.init_ui()
        self.layer_positions = []

    def init_ui(self):
        layout = QHBoxLayout(self)

        # Left panel (40%)
        left_panel = QVBoxLayout()
        self.open_btn = QPushButton("Open G-code")
        self.open_btn.clicked.connect(self.open_gcode)
        self.file_label = QLabel("No file loaded")
        self.info_label = QLabel("Print time: \nFilament used: ")
        left_panel.addWidget(self.open_btn)
        left_panel.addWidget(self.file_label)
        left_panel.addWidget(self.info_label)

        # Layer dropdown
        self.layer_label = QLabel("Layers:")
        self.layer_combo = QComboBox()
        self.layer_combo.currentIndexChanged.connect(self.goto_layer)
        left_panel.addWidget(self.layer_label)
        left_panel.addWidget(self.layer_combo)
        left_panel.addStretch()

        # Right panel (60%)
        self.gcode_view = QTextEdit()
        self.gcode_view.setReadOnly(True)

        # Add to main layout
        layout.addLayout(left_panel, 2)
        layout.addWidget(self.gcode_view, 3)

    def open_gcode(self):
        fname, _ = QFileDialog.getOpenFileName(
            self, "Open G-code", "", "G-code Files (*.gcode *.txt)"
        )
        if fname:
            self.file_label.setText(f"File: {fname.split('/')[-1]}")
            self.gcode_view.setPlainText("Loading...")
            self.layer_combo.clear()
            self.layer_combo.setEnabled(False)
            self.info_label.setText("Print time: \nFilament used: ")
            self.loader_thread = GCodeLoader(fname)
            self.loader_thread.loaded.connect(self.on_gcode_loaded)
            self.loader_thread.start()

    def on_gcode_loaded(self, gcode):
        self.gcode_view.setPlainText(gcode)
        self.update_info(gcode)
        self.populate_layers(gcode)

    def update_info(self, gcode):
        # Simple parsing for print time and filament used (look for comments)
        time_match = re.search(r';\s*TIME:\s*(\d+)', gcode)
        filament_match = re.search(r';\s*Filament used:\s*([\d\.]+)\s*m', gcode)
        time_str = f"{int(time_match.group(1)) // 60} min" if time_match else "Unknown"
        filament_str = f"{filament_match.group(1)} m" if filament_match else "Unknown"
        self.info_label.setText(f"Print time: {time_str}\nFilament used: {filament_str}")

    def populate_layers(self, gcode):
        # Find all layer change comments, but ignore ";Layer height:"
        self.layer_combo.clear()
        self.layer_positions = []
        lines = gcode.splitlines()
        for idx, line in enumerate(lines):
            # Ignore lines like ";Layer height: 0.2"
            if re.match(r';\s*Layer height:', line, re.IGNORECASE):
                continue
            # Match actual layer change comments
            if (
                re.match(r';\s*LAYER[:\s]', line, re.IGNORECASE)
                or re.match(r';\s*LAYER_CHANGE', line, re.IGNORECASE)
                or re.match(r';\s*layer\s', line, re.IGNORECASE)
            ):
                self.layer_combo.addItem(f"Layer {len(self.layer_positions)}")
                pos = self._line_to_position(gcode, idx)
                self.layer_positions.append(pos)
        if self.layer_combo.count() == 0:
            self.layer_combo.addItem("No layers found")
            self.layer_combo.setEnabled(False)
        else:
            self.layer_combo.setEnabled(True)

    def _line_to_position(self, gcode, line_number):
        # Helper: get character position at start of line_number
        lines = gcode.splitlines(keepends=True)
        return sum(len(lines[i]) for i in range(line_number))

    def goto_layer(self, index):
        if not self.layer_positions or index < 0 or index >= len(self.layer_positions):
            self.gcode_view.setExtraSelections([])  # Clear highlights
            return
        cursor = self.gcode_view.textCursor()
        cursor.setPosition(self.layer_positions[index])
        self.gcode_view.setTextCursor(cursor)
        self.gcode_view.setFocus()

        # Highlight the layer line
        gcode = self.gcode_view.toPlainText()
        start = self.layer_positions[index]
        end = gcode.find('\n', start)
        if end == -1:
            end = len(gcode)
        selection = QTextEdit.ExtraSelection()
        selection.cursor = self.gcode_view.textCursor()
        selection.cursor.setPosition(start)
        selection.cursor.setPosition(end, QTextCursor.KeepAnchor)
        selection.format.setBackground(QColor("#2aa6e9"))  # Light blue
        self.gcode_view.setExtraSelections([selection])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewer = GCodeViewer()
    viewer.show()
    sys.exit(app.exec_())