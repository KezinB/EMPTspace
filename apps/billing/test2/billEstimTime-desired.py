import sys
import numpy as np
from stl import mesh
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
    QHBoxLayout, QMessageBox, QSplitter, QFileDialog, QTabWidget, QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

class STLViewer(gl.GLViewWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor('k')
        self.mesh_item = None
        self.setCameraPosition(distance=200, elevation=30, azimuth=45)
        
    def load_stl(self, file_path):
        if self.mesh_item is not None:
            self.removeItem(self.mesh_item)
            self.mesh_item = None
        
        try:
            stl_mesh = mesh.Mesh.from_file(file_path)
            points = stl_mesh.points.reshape(-1, 3)
            faces = np.arange(points.shape[0]).reshape(-1, 3)
            
            mesh_data = gl.MeshData(vertexes=points, faces=faces)
            
            self.mesh_item = gl.GLMeshItem(
                meshdata=mesh_data, 
                color=(0.7, 0.7, 0.7, 1.0),
                drawEdges=True,
                edgeColor=(1, 1, 1, 1),
                shader='shaded'
            )
            self.addItem(self.mesh_item)
            self.reset_camera()
            
        except Exception as e:
            QMessageBox.critical(self, "STL Error", f"Error loading STL file:\n{str(e)}")

    def reset_camera(self):
        self.setCameraPosition(distance=200, elevation=30, azimuth=45)

class PrintCostCalculator(QWidget):
    stl_file_loaded = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.inputs = {}

        fields = {
            "Weight (grams)": "weight",
            "Print Time (hours)": "time",
            "Post-processing Cost (₹)": "post",
            "Profit Margin (%)": "profit"
        }

        for label_text, key in fields.items():
            hbox = QHBoxLayout()
            label = QLabel(label_text)
            input_field = QLineEdit()
            if key == "post":
                input_field.setText("20")
            elif key == "profit":
                input_field.setText("30")
            self.inputs[key] = input_field

            hbox.addWidget(label)
            hbox.addWidget(input_field)
            layout.addLayout(hbox)

        self.stl_button = QPushButton("Load STL File")
        self.stl_button.clicked.connect(self.load_stl_file)
        layout.addWidget(self.stl_button)

        self.button = QPushButton("Calculate Price")
        self.button.clicked.connect(self.calculate_price)
        layout.addWidget(self.button)

        self.result_label = QLabel("")
        self.result_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.result_label)

        self.setLayout(layout)

    def load_stl_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open STL File", "", "STL Files (*.stl)"
        )
        if file_path:
            self.stl_file_loaded.emit(file_path)

    def calculate_price(self):
        try:
            weight = float(self.inputs["weight"].text())
            time = float(self.inputs["time"].text())
            post = float(self.inputs["post"].text())
            profit = float(self.inputs["profit"].text())

            cost_per_gram = 0.7
            electricity_rate = 8
            power_usage_kw = 0.12
            machine_rate = 50

            material_cost = weight * cost_per_gram
            electricity_cost = power_usage_kw * time * electricity_rate
            machine_cost = machine_rate * time
            total_cost = material_cost + electricity_cost + machine_cost + post
            final_price = total_cost * (1 + profit / 100)

            self.result_label.setText(
                f"Material: ₹{material_cost:.2f}\n"
                f"Electricity: ₹{electricity_cost:.2f}\n"
                f"Machine: ₹{machine_cost:.2f}\n"
                f"Post-processing: ₹{post:.2f}\n"
                f"Total Cost: ₹{total_cost:.2f}\n"
                f"Final Price: ₹{final_price:.0f}"
            )

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numbers in all fields.")

class GCodeAnalyzer(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.browse_button = QPushButton("Browse G-code")
        self.browse_button.clicked.connect(self.browse_gcode)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.browse_button)
        layout.addLayout(file_layout)
        
        # Analysis button
        self.analyze_button = QPushButton("Analyze G-code")
        self.analyze_button.clicked.connect(self.analyze_gcode)
        layout.addWidget(self.analyze_button)
        
        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.results_text)
        
        self.setLayout(layout)
    
    def browse_gcode(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open G-code File", "", "G-code Files (*.gcode)"
        )
        if file_path:
            self.file_path = file_path
            self.file_label.setText(file_path.split('/')[-1])
    
    def analyze_gcode(self):
        if not hasattr(self, 'file_path'):
            QMessageBox.warning(self, "Error", "Please select a G-code file first.")
            return
            
        try:
            metadata = self.parse_gcode_metadata(self.file_path)
            self.display_results(metadata)
        except Exception as e:
            QMessageBox.critical(self, "Analysis Error", f"Failed to analyze G-code:\n{str(e)}")
    
    def parse_gcode_metadata(self, filename):
        metadata = {
            "flavor": "Unknown",
            "time": 0,
            "filament": "0m",
            "layer_height": 0.0,
            "minx": 0.0,
            "miny": 0.0,
            "minz": 0.0,
            "maxx": 0.0,
            "maxy": 0.0,
            "maxz": 0.0,
            "printer": "Unknown",
            "slicer": "Unknown"
        }

        try:
            with open(filename, 'r') as file:
                for line in file:
                    line = line.strip()
                    if line.startswith(';FLAVOR:'):
                        metadata["flavor"] = line.split(':', 1)[1].strip()
                    elif line.startswith(';TIME:'):
                        metadata["time"] = int(line.split(':', 1)[1])
                    elif line.startswith(';Filament used:'):
                        metadata["filament"] = line.split(':', 1)[1].strip()
                    elif line.startswith(';Layer height:'):
                        metadata["layer_height"] = float(line.split(':', 1)[1])
                    elif line.startswith(';MINX:'):
                        metadata["minx"] = float(line.split(':', 1)[1])
                    elif line.startswith(';MINY:'):
                        metadata["miny"] = float(line.split(':', 1)[1])
                    elif line.startswith(';MINZ:'):
                        metadata["minz"] = float(line.split(':', 1)[1])
                    elif line.startswith(';MAXX:'):
                        metadata["maxx"] = float(line.split(':', 1)[1])
                    elif line.startswith(';MAXY:'):
                        metadata["maxy"] = float(line.split(':', 1)[1])
                    elif line.startswith(';MAXZ:'):
                        metadata["maxz"] = float(line.split(':', 1)[1])
                    elif line.startswith(';TARGET_MACHINE.NAME:'):
                        metadata["printer"] = line.split(':', 1)[1].strip()
                    elif line.startswith(';Generated with'):
                        metadata["slicer"] = line.split('with', 1)[1].strip()

                    if line.startswith(';LAYER_COUNT') or line.startswith('G1'):
                        break

        except Exception as e:
            raise RuntimeError(f"Error parsing G-code: {str(e)}")
            
        return metadata

    def display_results(self, metadata):
        hours = metadata['time'] // 3600
        minutes = (metadata['time'] % 3600) // 60
        seconds = metadata['time'] % 60
        
        result_text = (
            f"G-code Metadata:\n"
            f"-----------------\n"
            f"Flavor:         {metadata['flavor']}\n"
            f"Print Time:     {hours}h {minutes}m {seconds}s\n"
            f"Filament Used:  {metadata['filament']}\n"
            f"Layer Height:   {metadata['layer_height']} mm\n"
            f"Print Area (X): {metadata['minx']:.2f}–{metadata['maxx']:.2f} mm\n"
            f"Print Area (Y): {metadata['miny']:.2f}–{metadata['maxy']:.2f} mm\n"
            f"Print Area (Z): {metadata['minz']:.2f}–{metadata['maxz']:.2f} mm\n"
            f"Printer:        {metadata['printer']}\n"
            f"Slicer:         {metadata['slicer']}"
        )
        
        self.results_text.setText(result_text)

class PrintCalculatorWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (20%)
        self.calculator = PrintCostCalculator()
        splitter.addWidget(self.calculator)
        
        # Right panel (80%)
        self.viewer = STLViewer()
        self.viewer.reset_camera()
        splitter.addWidget(self.viewer)
        
        splitter.setSizes([300, 900])
        self.calculator.stl_file_loaded.connect(self.viewer.load_stl)
        main_layout.addWidget(splitter)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Print Studio")
        self.setGeometry(100, 100, 1200, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        
        # Create the two main tabs
        self.print_tab = PrintCalculatorWidget()
        self.gcode_tab = GCodeAnalyzer()
        
        # Add tabs to tab widget
        self.tabs.addTab(self.print_tab, "Print Calculator")
        self.tabs.addTab(self.gcode_tab, "G-code Analyzer")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)

if __name__ == "__main__":
    pg.setConfigOption('background', 'k')
    pg.setConfigOption('foreground', 'w')
    pg.setConfigOptions(antialias=True)
    
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    sys.exit(app.exec_())