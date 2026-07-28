"""Parse coverage.xml for module-by-module report."""
import xml.etree.ElementTree as ET

tree = ET.parse("coverage.xml")
root = tree.getroot()

print("=== MODULE-BY-MODULE COVERAGE ===")
for pkg in root.findall(".//package"):
    name = pkg.get("name")
    lr = float(pkg.get("line-rate"))
    if "observability" in name or "ai_research" in name:
        print(f"  {name}: {lr*100:.1f}%")

print(f"\n  Overall: {float(root.get('line-rate'))*100:.1f}%")
print(f"  Lines: {root.get('lines-covered')}/{root.get('lines-valid')}")

# Check for lowest coverage
lowest = ("", 1.0)
for pkg in root.findall(".//package"):
    name = pkg.get("name")
    lr = float(pkg.get("line-rate"))
    if "observability" in name or "ai_research" in name:
        if lr < lowest[1]:
            lowest = (name, lr)

print(f"\n  Lowest target module: {lowest[0]} at {lowest[1]*100:.1f}%")

