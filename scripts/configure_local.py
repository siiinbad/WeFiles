"""Initialize a local .env secret without printing or overwriting it."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
if not path.exists():
    path.write_text((root / ".env.example").read_text())
lines = path.read_text().splitlines()
found = False
for index, line in enumerate(lines):
    if line.startswith("SECRET_KEY="):
        found = True
        if not line.partition("=")[2].strip():
            lines[index] = "SECRET_KEY=" + secrets.token_urlsafe(64)
        break
if not found:
    lines.append("SECRET_KEY=" + secrets.token_urlsafe(64))
path.write_text("\n".join(lines) + "\n")
path.chmod(0o600)
print("Local .env is ready. Existing secrets and configuration were preserved.")
