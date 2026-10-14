import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
RELEASE.mkdir(exist_ok=True)

archive = shutil.make_archive(str(RELEASE / "catalogo-rede-plan-assiste-1.1.0-rc.1"), "zip", DIST)
payload = Path(archive).read_bytes()
(RELEASE / "SHA256SUMS.txt").write_text(
    f"{hashlib.sha256(payload).hexdigest()}  {Path(archive).name}\n", encoding="utf-8"
)
sbom = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "version": 1,
    "metadata": {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": {"type": "data", "name": "catalogo-rede-plan-assiste", "version": "1.1.0-rc.1"},
    },
    "components": [
        {"type": "library", "name": "requests", "version": "2.32.5"},
        {"type": "library", "name": "truststore", "version": "0.10.4"},
    ],
}
(RELEASE / "sbom.cdx.json").write_text(json.dumps(sbom, indent=2) + "\n", encoding="utf-8")
print(archive)
