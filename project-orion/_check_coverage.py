"""Parse coverage_sprint1.xml for module-by-module report."""
import xml.etree.ElementTree as ET

try:
    tree = ET.parse("coverage_sprint1.xml")
    root = tree.getroot()
except FileNotFoundError:
    print("coverage_sprint1.xml not found yet")
    exit()

print("=== MODULE-BY-MODULE COVERAGE (TARGET MODULES) ===")
for pkg in root.findall(".//package"):
    name = pkg.get("name")
    lr = float(pkg.get("line-rate"))
    if "observability" in name or "ai_research" in name:
        print(f"  {name}: {lr*100:.1f}%")

print(f"\n  Overall: {float(root.get('line-rate'))*100:.1f}%")
print(f"  Lines: {root.get('lines-covered')}/{root.get('lines-valid')}")

