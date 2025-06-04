import sys
import os
import numpy as np
from stl import mesh
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
    QHBoxLayout, QMessageBox, QSplitter, QFileDialog, QTabWidget, 
    QTextEdit, QGroupBox, QSizePolicy
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

class GCodeLoaderTab(QWidget):
    pricing_requested = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.metadata = None
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # File selection group
        file_group = QGroupBox("G-code File")
        file_layout = QVBoxLayout()
        
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("font-weight: bold; color: #555;")
        
        browse_button = QPushButton("Browse G-code")
        browse_button.clicked.connect(self.browse_gcode)
        browse_button.setStyleSheet("padding: 8px; font-weight: bold;")
        browse_button.setFixedWidth(250)    
        
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(browse_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Confirm button
        self.confirm_button = QPushButton("Confirm")
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.analyze_gcode)
        self.confirm_button.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 5px; font-size: 14pt; font-weight: bold;"
        )
        self.confirm_button.setFixedWidth(265)
        layout.addWidget(self.confirm_button)
        
        # Results display
        results_group = QGroupBox("G-code Analysis")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Courier", 10))
        self.results_text.setStyleSheet("""
            background-color: #f9f9f9;
            border: 1px solid #ddd;
            height: 200px;
            padding: 10px;
        """)
        self.results_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.results_text.setPlaceholderText("G-code analysis results will appear here...")
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Pricing button
        self.pricing_button = QPushButton("Pricing →")
        self.pricing_button.setEnabled(False)
        self.pricing_button.clicked.connect(self.go_to_pricing)
        self.pricing_button.setStyleSheet("""
            background-color: #2196F3; 
            color: white; 
            padding: 10px; 
            font-size: 14pt; 
            font-weight: bold;
            border-radius: 5px;
            """)
        self.pricing_button.setFixedWidth(250)
        layout.addWidget(self.pricing_button, 0, Qt.AlignRight)
        
        layout.addStretch(1)
        self.setLayout(layout)
    
    def browse_gcode(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open G-code File", "", "G-code Files (*.gcode)"
        )
        if file_path:
            self.file_path = file_path
            self.file_label.setText(f"Selected: {os.path.basename(file_path)}")
            self.confirm_button.setEnabled(True)
    
    def analyze_gcode(self):
        if not hasattr(self, 'file_path'):
            QMessageBox.warning(self, "Error", "Please select a G-code file first.")
            return
            
        try:
            self.metadata = self.parse_gcode_metadata(self.file_path)
            self.display_results()
            self.pricing_button.setEnabled(True)
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

    def display_results(self):
        hours = self.metadata['time'] // 3600
        minutes = (self.metadata['time'] % 3600) // 60
        seconds = self.metadata['time'] % 60
        
        result_text = (
            f"G-code Metadata:\n"
            f"-----------------\n"
            f"Flavor:         {self.metadata['flavor']}\n"
            f"Print Time:     {hours}h {minutes}m {seconds}s\n"
            f"Filament Used:  {self.metadata['filament']}\n"
            f"Layer Height:   {self.metadata['layer_height']} mm\n"
            f"Print Area (X): {self.metadata['minx']:.2f}–{self.metadata['maxx']:.2f} mm\n"
            f"Print Area (Y): {self.metadata['miny']:.2f}–{self.metadata['maxy']:.2f} mm\n"
            f"Print Area (Z): {self.metadata['minz']:.2f}–{self.metadata['maxz']:.2f} mm\n"
            f"Printer:        {self.metadata['printer']}\n"
            f"Slicer:         {self.metadata['slicer']}"
        )
        
        self.results_text.setText(result_text)
    
    def go_to_pricing(self):
        if self.metadata:
            # Convert time to hours for pricing calculation
            self.metadata["time_hours"] = self.metadata["time"] / 3600.0
            self.pricing_requested.emit(self.metadata)

class PricingTab(QWidget):
    stl_view_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.metadata = None
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header with back button
        header_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back to G-code")
        self.back_button.clicked.connect(lambda: self.stl_view_requested.emit())
        self.back_button.setStyleSheet("padding: 5px; font-weight: bold;")
        header_layout.addWidget(self.back_button)
        
        title = QLabel("Pricing Calculator")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #333;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Print time from G-code
        self.time_group = QGroupBox("Print Time from G-code")
        time_layout = QVBoxLayout()
        self.time_label = QLabel("No G-code data loaded")
        self.time_label.setStyleSheet("font-weight: bold;")
        time_layout.addWidget(self.time_label)
        self.time_group.setLayout(time_layout)
        layout.addWidget(self.time_group)
        
        # Material info from G-code
        self.material_group = QGroupBox("Material Estimate from G-code")
        material_layout = QVBoxLayout()
        self.material_label = QLabel("No G-code data loaded")
        self.material_label.setStyleSheet("font-weight: bold;")
        material_layout.addWidget(self.material_label)
        self.material_group.setLayout(material_layout)
        layout.addWidget(self.material_group)
        
        # Input fields
        input_group = QGroupBox("Cost Parameters")
        input_layout = QVBoxLayout()
        
        self.inputs = {}
        fields = {
            "Weight (grams)": "weight",
            "Post-processing Cost (₹)": "post",
            "Electricity Rate (₹/kWh)": "electricity_rate",
            "Machine Rate (₹/hour)": "machine_rate",
            "Profit Margin (%)": "profit"
        }

        for label_text, key in fields.items():
            hbox = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(200)
            input_field = QLineEdit()
            if key == "post":
                input_field.setText("20")
            elif key == "weight":
                input_field.setText()
            elif key == "profit":
                input_field.setText("30")
            elif key == "electricity_rate":
                input_field.setText("8")
            elif key == "machine_rate":
                input_field.setText("50")
            self.inputs[key] = input_field

            hbox.addWidget(label)
            hbox.addWidget(input_field)
            input_layout.addLayout(hbox)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Calculate button
        self.calc_button = QPushButton("Calculate Price")
        self.calc_button.clicked.connect(self.calculate_price)
        self.calc_button.setStyleSheet(
            "background-color: #FF9800; color: white; padding: 10px; font-size: 14pt; font-weight: bold;"
        )
        layout.addWidget(self.calc_button)
        
        # Results display
        self.result_label = QLabel("")
        self.result_label.setStyleSheet(
            "font-weight: bold; font-size: 12pt; background-color: #f0f0f0; padding: 15px; border: 1px solid #ddd;"
        )
        self.result_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.result_label)
        
        # STL viewer button
        stl_button = QPushButton("View STL File →")
        stl_button.clicked.connect(lambda: self.stl_view_requested.emit())
        stl_button.setStyleSheet(
            "background-color: #9C27B0; color: white; padding: 10px; font-size: 14pt; font-weight: bold;"
        )
        layout.addWidget(stl_button)
        
        layout.addStretch(1)
        self.setLayout(layout)
    
    def set_metadata(self, metadata):
        self.metadata = metadata
        hours = metadata['time'] // 3600
        minutes = (metadata['time'] % 3600) // 60
        self.time_label.setText(f"{hours} hours {minutes} minutes")
        
        # Calculate and display material estimate
        material_text = self.calculate_material(metadata['filament'])
        self.material_label.setText(material_text)
        
        # Pre-fill weight field if we have estimate
        if "weight" in material_text.lower():
            weight = float(material_text.split("≈")[1].split("g")[0].strip())
            self.inputs['weight'].setText(f"{weight:.1f}")

    def calculate_material(self, filament_str):
        """Calculate material weight from filament length string"""
        try:
            # Extract numerical value from string (e.g., "12.34m" -> 12.34)
            value_str = ''.join(filter(lambda x: x.isdigit() or x in ['.', ','], filament_str))
            value = float(value_str.replace(',', '.'))
            
            # Check units and convert to meters
            if "mm" in filament_str.lower():
                length_m = value / 1000.0  # Convert mm to meters
            else:
                length_m = value  # Assume meters if no unit specified
            
            # Calculate weight (density: 1.24 g/cm³ for PLA)
            # Volume = π * r² * length
            diameter = 1.75  # mm
            radius_mm = diameter / 2.0
            volume_mm3 = 3.14159 * radius_mm**2 * (length_m * 1000)
            volume_cm3 = volume_mm3 / 1000.0
            weight_g = volume_cm3 * 1.24  # Density
            
            return f"Filament: {filament_str} ≈ {weight_g:.1f}g"
            
        except Exception as e:
            print(f"Error calculating material: {e}")
            return f"Filament: {filament_str} (weight calculation failed)"

    def calculate_price(self):
        try:
            weight = float(self.inputs["weight"].text())
            post = float(self.inputs["post"].text())
            profit = float(self.inputs["profit"].text())
            electricity_rate = float(self.inputs["electricity_rate"].text())
            machine_rate = float(self.inputs["machine_rate"].text())
            
            # Get time from metadata
            if self.metadata and 'time_hours' in self.metadata:
                time = self.metadata['time_hours']
            else:
                raise ValueError("No time data available")
            
            # Constants
            cost_per_gram = 0.7
            power_usage_kw = 0.12

            # Calculations
            material_cost = weight * cost_per_gram
            electricity_cost = power_usage_kw * time * electricity_rate
            machine_cost = machine_rate * time
            total_cost = material_cost + electricity_cost + machine_cost + post
            final_price = total_cost * (1 + profit / 100)

            self.result_label.setText(
                f"Material Cost: ₹{material_cost:.2f}\n"
                f"Electricity Cost: ₹{electricity_cost:.2f}\n"
                f"Machine Time: ₹{machine_cost:.2f}\n"
                f"Post-processing: ₹{post:.2f}\n"
                f"TOTAL COST: ₹{total_cost:.2f}\n"
                f"FINAL PRICE: ₹{final_price:.0f}"
            )

        except Exception as e:
            QMessageBox.warning(self, "Input Error", f"Please check your inputs:\n{str(e)}")

class STLViewerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header with back button
        header_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back to Pricing")
        self.back_button.setStyleSheet("padding: 5px; font-weight: bold;")
        header_layout.addWidget(self.back_button)
        
        title = QLabel("STL Viewer")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #333;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # File info group
        file_group = QGroupBox("STL File Information")
        file_layout = QVBoxLayout()
        
        self.file_label = QLabel("No STL file loaded")
        self.file_label.setStyleSheet("font-weight: bold;")
        
        self.size_label = QLabel("File size: -")
        
        self.load_button = QPushButton("Load STL File")
        self.load_button.clicked.connect(self.load_stl)
        self.load_button.setStyleSheet("padding: 8px; font-weight: bold;")
        
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.size_label)
        file_layout.addWidget(self.load_button)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # STL viewer
        self.viewer = STLViewer()
        self.viewer.setMinimumSize(600, 400)
        layout.addWidget(self.viewer, 1)
        
        self.setLayout(layout)
    
    def load_stl(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open STL File", "", "STL Files (*.stl)"
        )
        if file_path:
            self.file_label.setText(f"File: {os.path.basename(file_path)}")
            self.size_label.setText(f"Size: {os.path.getsize(file_path)/1024:.2f} KB")
            self.viewer.load_stl(file_path)

class MainApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D Print Studio")
        self.setGeometry(100, 100, 1200, 700)
        self.init_ui()
        self.current_metadata = None

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ddd; }
            QTabBar::tab { 
                background: #f0f0f0; 
                color: #333; 
                padding: 10px 20px; 
                border: 1px solid #ddd; 
                border-bottom: none; 
                width: 150px; 
                font-size: 12px;
                border-top-left-radius: 4px; 
                border-top-right-radius: 4px; 
            }
            QTabBar::tab:selected { 
                background: #e0e0e0; 
                font-weight: bold; 
            }
        """)
        
        # Create the three tabs
        self.tab1 = GCodeLoaderTab()
        self.tab2 = PricingTab()
        self.tab3 = STLViewerTab()
        
        # Add tabs to tab widget
        self.tabs.addTab(self.tab1, "G-code Loader")
        self.tabs.addTab(self.tab2, "Pricing Calculator")
        self.tabs.addTab(self.tab3, "STL Viewer")
        
        # Connect signals
        self.tab1.pricing_requested.connect(self.handle_pricing_request)
        self.tab2.stl_view_requested.connect(self.handle_stl_view_request)
        self.tab3.back_button.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        self.tab2.back_button.clicked.connect(lambda: self.tabs.setCurrentIndex(0))
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def handle_pricing_request(self, metadata):
        self.current_metadata = metadata
        self.tab2.set_metadata(metadata)
        self.tabs.setCurrentIndex(1)  # Switch to Pricing tab
    
    def handle_stl_view_request(self):
        self.tabs.setCurrentIndex(2)  # Switch to STL Viewer tab

if __name__ == "__main__":
    pg.setConfigOption('background', 'k')
    pg.setConfigOption('foreground', 'w')
    pg.setConfigOptions(antialias=True)
    
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle("Fusion")
    
    window = MainApp()
    window.show()
    sys.exit(app.exec_())