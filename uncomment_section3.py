"""
Quick script to uncomment SECTION 3 pricing functions in app.py
"""

# Read the file
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find SECTION 3 and uncomment all lines until next section
in_section_3 = False
output_lines = []

for i, line in enumerate(lines):
    if '# SECTION 3: FRN PRICING ENGINE' in line and not in_section_3:
        in_section_3 = True
        output_lines.append(line)
        continue
    
    if in_section_3 and '# SECTION 4:' in line:
        in_section_3 = False
        output_lines.append(line)
        continue
    
    if in_section_3 and line.startswith('# '):
        # Uncomment the line (remove '# ' from start)
        uncommented = line[2:]
        output_lines.append(uncommented)
    else:
        output_lines.append(line)

# Write back
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(output_lines)

print("✓ Uncommented SECTION 3 pricing functions")
print(f"  Processed {len(lines)} lines")
