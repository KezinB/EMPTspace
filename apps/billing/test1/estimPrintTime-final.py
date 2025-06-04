def parse_gcode_metadata(filename):
    metadata = {
        "flavor": None,
        "time": None,
        "filament": None,
        "layer_height": None,
        "minx": None,
        "miny": None,
        "minz": None,
        "maxx": None,
        "maxy": None,
        "maxz": None,
        "printer": None,
        "slicer": None
    }

    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if line.startswith(';FLAVOR:'):
                metadata["flavor"] = line.split(':', 1)[1]
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
                break  # Stop parsing metadata once actual G-code starts

    return metadata

# Example usage:
gcode_file = r"C:\Users\kezin\OneDrive\Documents\business_ideas\EMPTSPACE\Gcode\CE3PRO_chargingdoc-Body.gcode"
meta = parse_gcode_metadata(gcode_file)

hours = meta['time'] // 3600
minutes = (meta['time'] % 3600) // 60

print("G-code Metadata:")
print(f"  Flavor: {meta['flavor']}")
print(f"  Print Time: {hours}h {minutes}m")
print(f"  Filament Used: {meta['filament']}")
print(f"  Layer Height: {meta['layer_height']} mm")
print(f"  Print Area (X,Y,Z): {meta['minx']}–{meta['maxx']} × {meta['miny']}–{meta['maxy']} × {meta['minz']}–{meta['maxz']} mm")
print(f"  Printer: {meta['printer']}")
print(f"  Slicer: {meta['slicer']}")