import sys
import numpy as np
from stl import mesh
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
    QHBoxLayout, QMessageBox, QSplitter, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from pyqtgraph.opengl import GLViewWidget, MeshData, GLMeshItem
import pyqtgraph as pg
import pyqtgraph.opengl as gl

class STLViewer(gl.GLViewWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor('k')
        self.mesh_item = None
        self.setCameraPosition(distance=200, elevation=30, azimuth=45)
        
    def load_stl(self, file_path):
        # Clear previous mesh
        if self.mesh_item is not None:
            self.removeItem(self.mesh_item)
            self.mesh_item = None
        
        try:
            # Load STL file
            stl_mesh = mesh.Mesh.from_file(file_path)
            points = stl_mesh.points.reshape(-1, 3)
            faces = np.arange(points.shape[0]).reshape(-1, 3)
            
            # Create mesh data
            mesh_data = MeshData(vertexes=points, faces=faces)
            
            # Create and add mesh item
            self.mesh_item = GLMeshItem(
                meshdata=mesh_data, 
                color=(0.7, 0.7, 0.7, 1.0),
                drawEdges=True,
                edgeColor=(1, 1, 1, 1),
                shader='shaded'
            )
            self.addItem(self.mesh_item)
            
            # Center the mesh
            self.reset_camera()
            
        except Exception as e:
            QMessageBox.critical(self, "STL Error", f"Error loading STL file:\n{str(e)}")

    def reset_camera(self):
        """Reset camera to default view"""
        self.setCameraPosition(
            distance=200,
            elevation=30,
            azimuth=45
        )

class PrintCostCalculator(QWidget):
    stl_file_loaded = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Print Price Calculator")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.inputs = {}

        # Define input fields and labels
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

        # STL Load Button
        self.stl_button = QPushButton("Load STL File")
        self.stl_button.clicked.connect(self.load_stl_file)
        layout.addWidget(self.stl_button)

        # Calculate Button
        self.button = QPushButton("Calculate Price")
        self.button.clicked.connect(self.calculate_price)
        layout.addWidget(self.button)

        # Result display
        self.result_label = QLabel("")
        self.result_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(self.result_label)

        self.setLayout(layout)

    def load_stl_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Open STL File", 
            "", 
            "STL Files (*.stl)"
        )
        if file_path:
            self.stl_file_loaded.emit(file_path)

    def calculate_price(self):
        try:
            weight = float(self.inputs["weight"].text())
            time = float(self.inputs["time"].text())
            post = float(self.inputs["post"].text())
            profit = float(self.inputs["profit"].text())

            # Constants
            cost_per_gram = 0.7  # ₹/g
            electricity_rate = 8  # ₹/kWh
            power_usage_kw = 0.12
            machine_rate = 50  # ₹/hr

            # Calculations
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

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Print Calculator with STL Viewer")
        self.setGeometry(100, 100, 1200, 600)
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
        
        # Set splitter sizes
        splitter.setSizes([300, 900])  # 20% : 80% ratio
        
        # Connect STL loading signal
        self.calculator.stl_file_loaded.connect(self.viewer.load_stl)
        
        main_layout.addWidget(splitter)

if __name__ == "__main__":
    # Configure pyqtgraph to use the same OpenGL options as PyQt5
    pg.setConfigOption('background', 'k')
    pg.setConfigOption('foreground', 'w')
    pg.setConfigOptions(antialias=True)
    
    app = QApplication(sys.argv)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start the application
    sys.exit(app.exec_())