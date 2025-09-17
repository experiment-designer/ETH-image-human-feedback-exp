#!/usr/bin/env python3
"""Iterate through images and collect LLM preference judgments."""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Iterable, Set

from openai import OpenAI


def load_image_as_data_url(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    if suffix not in {"jpg", "jpeg", "png", "webp"}:
        raise ValueError(f"Unsupported image type for {path}")

    mime = "jpeg" if suffix in {"jpg", "jpeg"} else suffix
    with path.open("rb") as handle:
        encoded = base64.b64encode(handle.read()).decode("ascii")
    return f"data:image/{mime};base64,{encoded}"


def iter_image_paths(root: Path, recursive: bool) -> Iterable[Path]:
    if recursive:
        yield from sorted(
            (p for p in root.rglob("*") if p.is_file()),
            key=lambda path: str(path.relative_to(root)),
        )
    else:
        yield from sorted((p for p in root.iterdir() if p.is_file()), key=lambda path: path.name)


def extract_json_object(text: str) -> dict[str, object]:
    """Pull out a JSON object even if the model wraps it in fences."""

    stripped = text.strip()

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        stripped = stripped[start : end + 1]

    return json.loads(stripped)


def load_skip_images() -> Set[str]:
    """Load images that should be skipped and auto-labeled as -1."""

    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    skip_file = repo_root / "js" / "skipImages.js"
    if not skip_file.exists():
        return set()

    text = skip_file.read_text(encoding="utf-8")
    start = text.find("[")
    end = text.find("]", start)
    if start == -1 or end == -1:
        return set()

    try:
        data = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        logging.warning("Unable to parse skipImages.js, proceeding without skips.")
        return set()

    return {str(item) for item in data}


def request_preference(
    client: OpenAI,
    model: str,
    prompt: str,
    image_data_url: str,
    max_retries: int,
    retry_delay: float,
) -> str:
    for attempt in range(1, max_retries + 1):
        try:
            response = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": image_data_url},
                        ],
                    }
                ],
            )
            return response.output_text
        except Exception as exc:  # noqa: BLE001
            logging.warning("Attempt %d failed: %s", attempt, exc)
            if attempt == max_retries:
                raise
            time.sleep(retry_delay * attempt)
    raise RuntimeError("Unreachable")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", type=Path, help="Directory containing images to evaluate")
    parser.add_argument("--style", required=True, help="Style or rubric prompt for the model")
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="Vision-capable model to use (default: %(default)s)",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively search image directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("preferences.jsonl"),
        help="Destination JSONL file (default: %(default)s)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of images to process",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Number of request retries on failure (default: %(default)s)",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Base delay between retries in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip images already present in the output file",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if not args.images.is_dir():
        logging.error("%s is not a directory", args.images)
        return 1

    skip_images_full = load_skip_images()

    root_images_path = args.images.resolve()
    skip_rel_paths: set[str] = set()
    for item in skip_images_full:
        candidate = Path(item)
        if not candidate.is_absolute():
            candidate = (Path(__file__).resolve().parent.parent / candidate).resolve()
        try:
            rel = candidate.relative_to(root_images_path)
            skip_rel_paths.add(rel.as_posix())
        except ValueError:
            # Allow matching against filename only as a fallback
            skip_rel_paths.add(candidate.name)

    client = OpenAI()

    processed: set[str] = set()
    if args.skip_existing and args.output.exists():
        with args.output.open() as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                path = record.get("image")
                if isinstance(path, str):
                    processed.add(path)
        logging.info("Loaded %d existing entries", len(processed))

    args.output.parent.mkdir(parents=True, exist_ok=True)

    completed = 0

    with args.output.open("a", encoding="utf-8") as writer:
        for image_path in iter_image_paths(args.images, args.recursive):
            rel_path = os.path.relpath(image_path, args.images)
            if args.skip_existing and rel_path in processed:
                logging.info("Skipping %s (already processed)", rel_path)
                continue

            normalized_rel = rel_path.replace("\\", "/")
            if normalized_rel in skip_rel_paths:
                logging.info("Skipping %s by policy; recording preference -1", rel_path)
                preference: object = -1
            else:
                try:
                    data_url = load_image_as_data_url(image_path)
                except ValueError as exc:
                    logging.warning("Skipping %s: %s", image_path, exc)
                    continue

                logging.info("Querying %s", rel_path)
                prompt = (
                    "You are an art reviewer. Follow the style guidance below and choose the single best "
                    "preference label."
                    "\nReturn only a strict JSON object in the format {\"preference\": \"<label>\"}. "
                    "Do not include explanations or additional fields."
                    "\n\nStyle guidance:\n" + args.style
                )

                try:
                    output_text = request_preference(
                        client,
                        args.model,
                        prompt,
                        data_url,
                        args.max_retries,
                        args.retry_delay,
                    )
                except Exception as exc:  # noqa: BLE001
                    logging.error("Failed to get preference for %s: %s", rel_path, exc)
                    continue

                try:
                    parsed = extract_json_object(output_text)
                except json.JSONDecodeError:
                    logging.error("Non-JSON response for %s: %s", rel_path, output_text)
                    continue

                preference_value = parsed.get("preference")
                if isinstance(preference_value, str):
                    preference = preference_value.strip()
                elif isinstance(preference_value, (int, float)):
                    preference = int(preference_value)
                else:
                    logging.error("Missing preference in response for %s: %s", rel_path, output_text)
                    continue

            record = {
                "image": rel_path,
                "model": args.model,
                "preference": preference,
            }
            writer.write(json.dumps(record) + "\n")
            writer.flush()

            processed.add(rel_path)
            completed += 1

            if args.limit is not None and completed >= args.limit:
                break

    logging.info("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
