import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QMessageBox
)

class PrintCostCalculator(QWidget):
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
            label = QLabel(label_text)
            input_field = QLineEdit()
            if key == "post":
                input_field.setText("20")
            elif key == "profit":
                input_field.setText("30")
            self.inputs[key] = input_field

            layout.addWidget(label)
            layout.addWidget(input_field)

        # Calculate Button
        self.button = QPushButton("Calculate Price")
        self.button.clicked.connect(self.calculate_price)
        layout.addWidget(self.button)

        # Result display
        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

        self.setLayout(layout)

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
                f"Total Cost: ₹{total_cost:.2f}\n"
                f"Final Price (with profit): ₹{final_price:.0f}"
            )

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numbers in all fields.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PrintCostCalculator()
    window.show()
    sys.exit(app.exec_())
