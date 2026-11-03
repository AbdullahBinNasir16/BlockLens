"""Generate the backend half of the API contract.

    python -m scripts.contract           # write blocklens/api/contract.py
    python -m scripts.contract --check   # exit 1 if it has drifted

Source: `contract/blocklens.schema.json`, itself generated from
`src/data/api.ts` (`node scripts/contract.mjs`). `npm run contract` runs both.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SCHEMA = BACKEND.parent / "contract" / "blocklens.schema.json"
OUT = BACKEND / "blocklens" / "api" / "contract.py"
HEADER = ('"""Generated from contract/blocklens.schema.json by scripts/contract.py. Do not edit:\n'
          'change src/data/api.ts and run `npm run contract`."""')


def generate() -> str:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "contract.py"
        subprocess.run([
            sys.executable, "-m", "datamodel_code_generator",
            "--input", str(SCHEMA), "--input-file-type", "jsonschema",
            "--output", str(out), "--output-model-type", "pydantic_v2.BaseModel",
            "--target-python-version", "3.12", "--use-standard-collections",
            "--use-union-operator", "--disable-timestamp", "--use-schema-description",
            "--custom-file-header", HEADER, "--formatters", "black",
        ], check=True)
        return out.read_text(encoding="utf8").replace("\r\n", "\n")


def main() -> None:
    fresh = generate()
    if "--check" in sys.argv:
        if OUT.read_text(encoding="utf8").replace("\r\n", "\n") != fresh:
            sys.exit(f"{OUT} is out of date: run npm run contract")
        print(f"{OUT} is up to date")
    else:
        OUT.write_text(fresh, encoding="utf8", newline="\n")
        print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
