"""
EMPTspace Studio - A 3D Printing Billing and Management Application 
Copyright (C) 2023 EMPTspace Studio 

developed by EMPTspace Studio Team
team lead by: Kezin B Wilson
"""

"""
major changes:
- update pdf generation to use reportlab
- add logo to invoice
- improve layout and styling of invoice

fixed: all known bugs

"""

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
import time
from fpdf import FPDF
from PyQt5.QtCore import QDateTime
from PyQt5.QtWidgets import QStatusBar 

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, inch
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Image, Spacer, SimpleDocTemplate, PageBreak
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

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
            self.window().status_message.setText("Error loading STL file")

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
            self.window().status_message.setText("Please select a G-code file first.")
            self.window().status_message.setStyleSheet("color: red; font-weight: bold;")
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
        self.window().status_message.setText("G-code analysis complete")

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
        self.final_price = 0.0  # Store final price for invoice
        
    def init_ui(self):
        # Create a horizontal splitter for 50/50 layout
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel (existing pricing calculator)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Header with back button
        header_layout = QHBoxLayout()
        self.back_button = QPushButton("← Back to G-code")
        self.back_button.clicked.connect(lambda: self.stl_view_requested.emit())
        self.back_button.setStyleSheet("padding: 5px; font-weight: bold;")
        header_layout.addWidget(self.back_button)
        
        title = QLabel("Pricing")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #333;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        left_layout.addLayout(header_layout)
        
        # Print time from G-code
        self.time_group = QGroupBox("Print Time from G-code")
        time_layout = QVBoxLayout()
        self.time_label = QLabel("No G-code data loaded")
        self.time_label.setStyleSheet("font-weight: bold;")
        time_layout.addWidget(self.time_label)
        self.time_group.setLayout(time_layout)
        left_layout.addWidget(self.time_group)
        
        # Material info from G-code
        self.material_group = QGroupBox("Material Estimate from G-code")
        material_layout = QVBoxLayout()
        self.material_label = QLabel("No G-code data loaded")
        self.material_label.setStyleSheet("font-weight: bold;")
        material_layout.addWidget(self.material_label)
        self.material_group.setLayout(material_layout)
        left_layout.addWidget(self.material_group)
        
        # Input fields
        input_group = QGroupBox("Cost Parameters")
        input_layout = QVBoxLayout()
        
        self.inputs = {}
        fields = {
            "Weight (grams)": "weight",
            "Post-processing Cost (Rs )": "post",
            "Electricity Rate (Rs /kWh)": "electricity_rate",
            "Machine Rate (Rs /hour)": "machine_rate",
            "Profit Margin (%)": "profit"
        }

        for label_text, key in fields.items():
            hbox = QHBoxLayout()
            label = QLabel(label_text)
            label.setMinimumWidth(200)
            input_field = QLineEdit()
            if key == "post":
                input_field.setText("20")
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
        left_layout.addWidget(input_group)
        
        # Calculate button
        self.calc_button = QPushButton("Calculate Price")
        self.calc_button.clicked.connect(self.calculate_price)
        self.calc_button.setStyleSheet(
            "background-color: #FF9800; color: white; padding: 10px; font-size: 14pt; font-weight: bold;"
        )
        left_layout.addWidget(self.calc_button)
        
        # Results display
        self.result_label = QLabel("")
        self.result_label.setStyleSheet(
            "font-weight: bold; font-size: 12pt; background-color: #f0f0f0; padding: 15px; border: 1px solid #ddd;"
        )
        self.result_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.result_label)
        
        left_layout.addStretch(1)
        
        # Right panel (customer details and invoice)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Customer details group
        customer_group = QGroupBox("Customer Details")
        customer_layout = QVBoxLayout()
        
        self.customer_fields = {}
        customer_info = {
            "Name": "name",
            "Phone": "phone",
            "Email": "email",
            "Address": "address"
        }
        
        for label_text, key in customer_info.items():
            vbox = QVBoxLayout()
            label = QLabel(label_text)
            input_field = QLineEdit()
            self.customer_fields[key] = input_field
            
            vbox.addWidget(label)
            vbox.addWidget(input_field)
            customer_layout.addLayout(vbox)
        
        customer_group.setLayout(customer_layout)
        right_layout.addWidget(customer_group)
        
        # Order details group
        order_group = QGroupBox("Order Information")
        order_layout = QVBoxLayout()
        
        # Generate order number
        self.order_number = f"ORD-{int(time.time())}"
        order_num_label = QLabel(f"Order #: {self.order_number}")
        order_num_label.setStyleSheet("font-weight: bold; color: #333;")
        order_layout.addWidget(order_num_label)
        
        # Order date
        self.order_date = QDateTime.currentDateTime().toString("dd MMM yyyy hh:mm AP")
        date_label = QLabel(f"Date: {self.order_date}")
        date_label.setStyleSheet("color: #555;")
        order_layout.addWidget(date_label)
        
        # Print details (will be populated later)
        self.print_details_label = QLabel("Print details will appear here")
        self.print_details_label.setWordWrap(True)
        self.print_details_label.setStyleSheet("background-color: #f9f9f9; padding: 10px; border: 1px solid #eee;")
        order_layout.addWidget(self.print_details_label)
        
        order_group.setLayout(order_layout)
        right_layout.addWidget(order_group)
        
        # Invoice button
        self.invoice_button = QPushButton("Generate Invoice (PDF)")
        self.invoice_button.setEnabled(False)
        self.invoice_button.clicked.connect(self.generate_invoice)
        self.invoice_button.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 10px; font-size: 14pt; font-weight: bold;"
        )
        right_layout.addWidget(self.invoice_button)
        
        right_layout.addStretch(1)
        
        # Add both widgets to splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([self.width()//2, self.width()//2])
        
        # Set main layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
    
    def set_metadata(self, metadata):
        self.metadata = metadata
        hours = metadata['time'] // 3600
        minutes = (metadata['time'] % 3600) // 60
        self.time_label.setText(f"{hours} hours {minutes} minutes")
        
        # Calculate and display material estimate
        weight_g = self.calculate_material(metadata['filament'])
        # self.material_label.setText(f"Filament: {metadata['filament']} ≈ {weight_g:.1f}g")
        self.material_label.setText(f"Filament: {metadata['filament']} ~ {weight_g:.1f}g")
        # self.material_label.setText(f"Filament: {metadata['filament']} approx. {weight_g:.1f}g")

        
        # Update weight input field with calculated value
        self.inputs['weight'].setText(f"{weight_g:.1f}")
        
        # Update print details in order info
        self.update_print_details()

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
            volume_mm3 = 3.14159 * radius_mm**2 * (length_m * 1000)  # Convert length to mm
            volume_cm3 = volume_mm3 / 1000.0
            weight_g = volume_cm3 * 1.24  # Density
            
            return weight_g
            
        except Exception as e:
            print(f"Error calculating material: {e}")
            QMessageBox.warning(self, "Material Calculation Error", 
                                f"Failed to calculate material weight:\n{str(e)}")
            self.window().status_message.setText("Error calculating material weight")
            return 0.0  # Return 0 on error

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

            # Store final price for invoice
            self.final_price = final_price
            
            # Enable invoice button
            self.invoice_button.setEnabled(True)
            
            # Update result label
            self.result_label.setText(
                f"Material Cost: Rs{material_cost:.2f}\n"
                f"Electricity Cost: Rs {electricity_cost:.2f}\n"
                f"Machine Time: Rs {machine_cost:.2f}\n"
                f"Post-processing: Rs {post:.2f}\n"
                f"TOTAL COST: Rs {total_cost:.2f}\n"
                f"FINAL PRICE: Rs {final_price:.0f}"
            )
            
            # Update print details with pricing
            self.update_print_details()
            self.window().status_message.setText("Pricing calculated successfully")
            self.print_details_label.setText(
                self.print_details_label.text() + 
                f"\nFinal Price: Rs {final_price:.0f}"
            )

        except Exception as e:
            QMessageBox.warning(self, "Input Error", f"Please check your inputs:\n{str(e)}")
            self.window().status_message.setText("Please check your inputs")
            self.window().status_message.setStyleSheet("color: red; font-weight: bold;")
            
    def update_print_details(self):
        if not self.metadata:
            return
            
        details = (
            f"Print Time: {self.time_label.text()}\n"
            f"Material: {self.material_label.text()}\n"
        )
        self.print_details_label.setText(details)
    
    def generate_invoice(self):
        # Validate customer details
        if not all(self.customer_fields[field].text().strip() for field in ['name', 'phone']):
            QMessageBox.warning(self, "Missing Information", "Please fill in at least Name and Phone fields")
            self.window().status_message.setText("Please fill in all required fields.")
            return
        
        try:
            # Get customer details
            customer = {key: field.text() for key, field in self.customer_fields.items()}
            
            # Generate PDF filename
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Invoice", 
                f"Invoice_{self.order_number}.pdf", 
                "PDF Files (*.pdf)"
            )
            
            if not filename:
                return  # User canceled
                
            # Create PDF document
            doc = SimpleDocTemplate(
                filename,
                pagesize=letter,
                leftMargin=40,
                rightMargin=40,
                topMargin=60,
                bottomMargin=60
            )
            
            # Define styles with unique names
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='InvoiceTitle',
                parent=styles['Title'],
                fontName='Helvetica-Bold',
                fontSize=16,
                alignment=TA_CENTER,
                spaceAfter=12
            ))
            styles.add(ParagraphStyle(
                name='InvoiceHeading',
                parent=styles['Heading2'],
                fontName='Helvetica-Bold',
                fontSize=12,
                spaceAfter=4
            ))
            styles.add(ParagraphStyle(
                name='InvoiceBody',
                parent=styles['BodyText'],
                fontName='Helvetica',
                fontSize=10
            ))
            styles.add(ParagraphStyle(
                name='InvoiceTableHeader',
                parent=styles['BodyText'],
                fontName='Helvetica-Bold',
                fontSize=10,
                alignment=TA_CENTER
            ))
            styles.add(ParagraphStyle(
                name='InvoiceFooter',
                parent=styles['BodyText'],
                fontName='Helvetica',
                fontSize=8,
                textColor=colors.grey
            ))
            styles.add(ParagraphStyle(
                name='InvoiceSignature',
                parent=styles['BodyText'],
                fontName='Helvetica',
                fontSize=8,
                textColor=colors.darkgrey,
                alignment=TA_CENTER,
                spaceBefore=15,
                italic=True
            ))
            
            # Create story (content elements)
            story = []
            
            # Add logo and title in a table for better layout
            logo_path = "logoMain.png"  # Update with your logo path
            # if os.path.exists(logo_path):
            #     logo = Image(logo_path, width=202, height=62)
            #     # Create table with logo and title
            #     header_table = Table([
            #         [logo, Paragraph("INVOICE", styles['InvoiceTitle'])]
            #     ], colWidths=[150, 350])
            #     header_table.setStyle(TableStyle([
            #         ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            #         ('ALIGN', (0,0), (0,0), 'RIGHT'),
            #         ('ALIGN', (1,0), (1,0), 'LEFT'),
            #     ]))
            #     story.append(header_table)
            # else:
            #     # If no logo, just show title
            #     story.append(Paragraph("INVOICE", styles['InvoiceTitle']))
            
            # story.append(Spacer(1, 10))
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=202, height=62)
                # Create table with logo on top and title below
                header_table = Table([
                    [logo],  # Logo in first row
                    [Paragraph("INVOICE", styles['InvoiceTitle'])]  # Title in second row
                ], colWidths=[200])  # Adjust width if needed
                
                header_table.setStyle(TableStyle([
                    ('ALIGN', (0,0), (0,0), 'CENTER'),  # Center logo
                    ('ALIGN', (0,1), (0,1), 'CENTER'),  # Center title
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE')  # Ensure vertical alignment
                ]))
                
                story.append(header_table)
            else:
                # If no logo, just show title
                story.append(Paragraph("INVOICE", styles['InvoiceTitle']))

            story.append(Spacer(1, 10))
            
            # Add horizontal line separator
            separator = Table([[""]], colWidths=[500], style=[
                ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.lightgrey)
            ])
            story.append(separator)
            story.append(Spacer(1, 15))
            
            # Order information
            order_info = [
                [Paragraph("Order #", styles['InvoiceBody']), Paragraph(self.order_number, styles['InvoiceBody'])],
                [Paragraph("Date", styles['InvoiceBody']), Paragraph(self.order_date, styles['InvoiceBody'])]
            ]
            
            order_table = Table(order_info, colWidths=[100, 200])
            order_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5)
            ]))
            story.append(order_table)
            story.append(Spacer(1, 15))
            
            # Customer information
            story.append(Paragraph("Bill To:", styles['InvoiceHeading']))
            customer_info = [
                [Paragraph("Name:", styles['InvoiceBody']), Paragraph(customer['name'], styles['InvoiceBody'])],
                [Paragraph("Phone:", styles['InvoiceBody']), Paragraph(customer['phone'], styles['InvoiceBody'])]
            ]
            
            if customer['email']:
                customer_info.append([Paragraph("Email:", styles['InvoiceBody']), Paragraph(customer['email'], styles['InvoiceBody'])])
            if customer['address']:
                customer_info.append([Paragraph("Address:", styles['InvoiceBody']), Paragraph(customer['address'], styles['InvoiceBody'])])
            
            cust_table = Table(customer_info, colWidths=[60, 240])
            cust_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3)
            ]))
            story.append(cust_table)
            
            # Add horizontal line separator
            story.append(Spacer(1, 10))
            story.append(separator)
            story.append(Spacer(1, 15))
            
            # Print details
            story.append(Paragraph("Print Details", styles['InvoiceHeading']))
            print_details = self.print_details_label.text().split('\n')
            for detail in print_details:
                if detail:  # Skip empty lines
                    story.append(Paragraph(detail, styles['InvoiceBody']))
            
            # Add horizontal line separator
            story.append(Spacer(1, 15))
            story.append(separator)
            story.append(Spacer(1, 15))
            
            # Pricing breakdown table
            story.append(Paragraph("Pricing Breakdown", styles['InvoiceHeading']))
            
            # Prepare table data
            breakdown = self.result_label.text().split('\n')
            table_data = [
                [Paragraph("Description", styles['InvoiceTableHeader']), 
                Paragraph("Amount (Rs)", styles['InvoiceTableHeader'])]
            ]
            
            for line in breakdown[:-1]:  # Skip final price line
                if line:
                    parts = line.split(':')
                    if len(parts) == 2:
                        table_data.append([
                            Paragraph(parts[0].strip(), styles['InvoiceBody']),
                            Paragraph(parts[1].strip(), styles['InvoiceBody'])
                        ])
            
            # Add total row
            table_data.append([
                Paragraph("TOTAL COST", styles['InvoiceBody']),
                Paragraph(f"Rs {self.final_price:.2f}", styles['InvoiceBody'])
            ])
            
            # Create table
            pricing_table = Table(table_data, colWidths=[350, 100])
            pricing_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 10),
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
                ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold', 10),
            ]))
            
            story.append(pricing_table)
            
            # Add horizontal line separator
            story.append(Spacer(1, 15))
            story.append(separator)
            
            # Add signature note
            story.append(Paragraph("Auto-generated invoice - No signature required", styles['InvoiceSignature']))
            story.append(Spacer(1, 20))
            
            # Footer
            footer = [
                Paragraph("Thank you for your business!", styles['InvoiceBody']),
                Paragraph("EMPTspace inc.", styles['InvoiceBody']),
                Paragraph("123 Innovation Street, Tech City", styles['InvoiceFooter']),
                Paragraph("Phone: +1 (555) 123-4567 | Email: info@emptspace.com", styles['InvoiceFooter'])
            ]
            
            for item in footer:
                story.append(item)
                story.append(Spacer(1, 3))
            
            # Build PDF
            doc.build(story)
            
            # Show success message
            QMessageBox.information(self, "Invoice Generated", 
                                f"Invoice saved successfully as:\n{filename}")
            self.window().status_message.setText("Invoice generated successfully")
            self.window().status_message.setStyleSheet("color: green; font-weight: bold;")
            
        except Exception as e:
            QMessageBox.critical(self, "PDF Error", f"Failed to generate PDF:\n{str(e)}")
            self.window().status_message.setText("Error generating invoice")
            self.window().status_message.setStyleSheet("color: red; font-weight: bold;")

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
        self.setWindowTitle("EMPT Studio")
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
        
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f0f0f0;
                color: #333;
                border-top: 1px solid #ddd;
                padding: 2px;
            }
        """)
        
        # Add company name to status bar
        self.status_message = QLabel("Ready")
        self.status_bar.addWidget(self.status_message, 1)  # Make it expandable
        
        company_label = QLabel("EMPTspace inc.")
        company_label.setStyleSheet("font-weight: bold; padding-left: 10px;")
        company_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.status_bar.addPermanentWidget(company_label)             
        
        layout.addWidget(self.tabs)
        layout.addWidget(self.status_bar)
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