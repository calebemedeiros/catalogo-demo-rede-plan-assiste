import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
if DIST.exists(): shutil.rmtree(DIST)
shutil.copytree(ROOT / "api", DIST / "api")
for name in ["README.md","SECURITY.md"]:
    shutil.copy2(ROOT / name, DIST / name)
release = ROOT / "release"
release.mkdir(exist_ok=True)
archive = shutil.make_archive(str(release / "catalogo-rede-plan-assiste-1.0.0-rc.1"), "zip", DIST)
payload = Path(archive).read_bytes()
(release / "SHA256SUMS.txt").write_text(f"{hashlib.sha256(payload).hexdigest()}  {Path(archive).name}\n", encoding="utf-8")
sbom = {"bomFormat":"CycloneDX","specVersion":"1.5","version":1,"metadata":{"timestamp":datetime.now(timezone.utc).isoformat(),"component":{"type":"data","name":"catalogo-rede-plan-assiste","version":"1.0.0-rc.1"}},"components":[{"type":"library","name":"openpyxl","version":"3.1.5"},{"type":"library","name":"requests","version":"2.32.5"}]}
(release / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2)+"\n", encoding="utf-8")
print(archive)
