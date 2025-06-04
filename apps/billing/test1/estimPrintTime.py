import re

def parse_gcode(file_path):
    total_time_sec = 0
    total_extrusion = 0

    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith("G1") or line.startswith("G0"):  # Movement commands
                speed_match = re.search(r'F(\d+)', line)
                extrusion_match = re.search(r'E([\d.]+)', line)

                if speed_match:
                    speed = float(speed_match.group(1)) / 60  # Convert mm/min to mm/sec
                    total_time_sec += 1 / speed  # Approximate time per move

                if extrusion_match:
                    total_extrusion += float(extrusion_match.group(1))

    total_time_hours = total_time_sec / 3600  # Convert seconds to hours
    return total_time_hours, total_extrusion

print_time, material_used = parse_gcode(r"C:\Users\kezin\OneDrive\Documents\business_ideas\EMPTSPACE\Gcode\3DBenchy_1h51m_0.20mm_205C_PLA_ENDER3.gcode")
print(f"Estimated Print Time: {print_time:.2f} hours")
print(f"Material Used: {material_used:.2f} mm")