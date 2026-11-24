import csv
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import yaml

from reader import read_csv
from transformer import load_column_mapping, rename_columns

logger = logging.getLogger(__name__)


def _sha256(path: Path) -> str:
    """Return the SHA-256 hash of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, data: object) -> None:
    """Write JSON to a temporary file, then replace the target."""
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _get_column_mapping(
    all_mappings: dict,
    input_path: Path,
) -> dict[str, str]:
    """Get this input file's column mapping, if one is configured."""
    file_mapping = all_mappings.get(input_path.name)
    if file_mapping is None:
        file_mapping = all_mappings.get(input_path.stem)

    # Also accept a single mapping of old column name -> new column name.
    if file_mapping is None and all(
        isinstance(value, str) for value in all_mappings.values()
    ):
        file_mapping = all_mappings

    return file_mapping or {}


def run_pipeline(config_path: str = "config/config.yaml") -> dict:
    """Process new or changed CSV files using the YAML configuration."""
    started = time.perf_counter()
    timestamp = datetime.now().astimezone().isoformat(timespec="seconds")

    config_file = Path(config_path).resolve()
    project_dir = config_file.parent.parent

    config = yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    paths = config["paths"]
    processing = config.get("processing", {})

    input_dir = project_dir / paths["input_dir"]
    output_dir = project_dir / paths["output_dir"]
    log_dir = project_dir / paths["log_dir"]
    manifest_path = project_dir / paths["manifest"]

    output_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"run_{datetime.now():%Y%m%d_%H%M%S}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )

    logger.info("Pipeline started")

    mapping_path = paths.get("column_mapping_json")
    if mapping_path:
        all_mappings = load_column_mapping(project_dir / mapping_path)
    else:
        all_mappings = config.get("mappings", {})

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {}

    processed_files = 0
    skipped_files = 0
    failed_files = 0
    input_rows = 0
    output_rows = 0

    input_glob = processing.get("input_glob", "*.csv")

    for input_path in sorted(input_dir.glob(input_glob)):
        try:
            file_hash = _sha256(input_path)
            old_entry = manifest.get(input_path.name, {})
            csv_output = output_dir / f"{input_path.stem}_cleaned.csv"
            json_output = output_dir / f"{input_path.stem}_cleaned.json"

            outputs_exist = csv_output.exists() and json_output.exists()
            if old_entry.get("sha256") == file_hash and outputs_exist:
                skipped_files += 1
                logger.info("Skipped unchanged file: %s", input_path.name)
                continue

            logger.info("Processing file: %s", input_path.name)
            rows = read_csv(input_path)
            input_rows += len(rows)

            column_mapping = _get_column_mapping(all_mappings, input_path)
            cleaned_rows = [
                rename_columns(row, column_mapping)
                for row in rows
            ]

            if cleaned_rows:
                fieldnames = list(cleaned_rows[0].keys())
            else:
                fieldnames = []

            with csv_output.open("w", encoding="utf-8", newline="") as file:
                if fieldnames:
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(cleaned_rows)

            _write_json(json_output, cleaned_rows)

            manifest[input_path.name] = {
                "sha256": file_hash,
                "processed_at": timestamp,
                "csv_output": csv_output.name,
                "json_output": json_output.name,
            }
            _write_json(manifest_path, manifest)

            processed_files += 1
            output_rows += len(cleaned_rows)

        except Exception:
            failed_files += 1
            logger.exception("Failed to process %s", input_path.name)

    summary = {
        "timestamp": timestamp,
        "files_processed": processed_files,
        "files_skipped": skipped_files,
        "files_failed": failed_files,
        "input_rows": input_rows,
        "output_rows": output_rows,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "log_file": str(log_file),
    }

    _write_json(output_dir / "run_summary.json", summary)
    logger.info("Pipeline finished: %s", summary)
    return summary