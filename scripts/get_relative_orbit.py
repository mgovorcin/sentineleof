#!/usr/bin/env python
"""
Estimate Sentinel-1 relative orbit directly from SAFE metadata.

Works for S1A/B/C/D — reads relativeOrbitNumber from manifest.safe.
Accepts .SAFE directory or .SAFE.zip.

Usage
-----
python get_relative_orbit.py <path_to_SAFE_or_zip>
"""
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"safe": "http://www.esa.int/safe/sentinel-1.0",
      "s1":   "http://www.esa.int/safe/sentinel-1.0/sentinel-1"}

def read_manifest(safe_path: str) -> ET.Element:
    p = Path(safe_path)
    if p.suffix == ".zip":
        with zipfile.ZipFile(p) as zf:
            manifest = next(f for f in zf.namelist() if f.endswith("manifest.safe"))
            return ET.parse(zf.open(manifest)).getroot()
    else:
        return ET.parse(p / "manifest.safe").getroot()

def get_relative_orbit(safe_path: str) -> dict:
    root = read_manifest(safe_path)

    def find(tag):
        for el in root.iter():
            if el.tag.split("}")[-1] == tag:
                return el
        return None

    rel_orbit = find("relativeOrbitNumber")
    abs_orbit = find("orbitNumber")
    direction = find("pass")
    ant       = find("ascendingNodeTime")
    mission   = find("familyName")  # e.g. SENTINEL-1

    # Also grab mission from filename
    import re
    safe_name = Path(safe_path).stem.replace(".SAFE", "")
    m = re.match(r"(S1[A-Z])", safe_name)
    satellite = m.group(1) if m else "unknown"

    result = {
        "satellite":           satellite,
        "absolute_orbit":      int(abs_orbit.text) if abs_orbit is not None else None,
        "relative_orbit":      int(rel_orbit.text) if rel_orbit is not None else None,
        "orbit_direction":     direction.text if direction is not None else None,
        "ascending_node_time": ant.text if ant is not None else None,
    }

    # Derive offset for formula: rel = (abs - offset) % 175 + 1
    if result["absolute_orbit"] and result["relative_orbit"]:
        abs_o = result["absolute_orbit"]
        rel_o = result["relative_orbit"]
        # offset = abs - (rel - 1) mod 175; pick smallest positive value < 175
        offset_mod = (abs_o - (rel_o - 1)) % 175
        result["derived_offset_mod175"] = offset_mod
        result["formula_check"] = (abs_o - offset_mod) % 175 + 1

    return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_relative_orbit.py <SAFE_or_zip>")
        sys.exit(1)

    info = get_relative_orbit(sys.argv[1])
    print(f"Satellite:            {info['satellite']}")
    print(f"Absolute orbit:       {info['absolute_orbit']}")
    print(f"Relative orbit:       {info['relative_orbit']}")
    print(f"Orbit direction:      {info['orbit_direction']}")
    print(f"Ascending node time:  {info['ascending_node_time']}")
    if "derived_offset_mod175" in info:
        print(f"Derived offset mod175: {info['derived_offset_mod175']}")
        print(f"Formula check:        ({info['absolute_orbit']} - {info['derived_offset_mod175']}) % 175 + 1 = {info['formula_check']}")
