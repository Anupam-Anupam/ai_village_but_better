import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


def is_agent_response(filename: str, data: Dict) -> bool:
    name = filename.lower()
    if "agent_response" in name or "agent-response" in name:
        return True
    # Heuristic: messages from agent/assistant
    if isinstance(data, dict):
        # CUA logs often have a list under "output" with type/message
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict) and item.get("type") == "message":
                    content = item.get("content", [])
                    if content:
                        return True
        # Lite logs may contain role-based messages
        role = data.get("role")
        if role == "assistant":
            return True
    return False


def is_screenshot_like(filename: str, data: Dict) -> bool:
    name = filename.lower()
    # File-name hints
    if "screenshot" in name or "computer_call_result" in name or "annotated" in name:
        return True
    # Content hints
    if isinstance(data, dict):
        # Look for entries that indicate a screenshot/computer output event
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict) and item.get("type") in {"computer_call_output", "computer_call"}:
                    return True
        if any(k in data for k in ["screenshot", "image", "image_path", "screenshot_path"]):
            return True
    return False


def collect_json_files(root: Path) -> List[Path]:
    return [p for p in root.rglob("*.json") if p.is_file()]


def classify_files(files: List[Path]) -> Tuple[List[Path], List[Path], List[Path]]:
    screenshots: List[Path] = []
    agent_responses: List[Path] = []
    other: List[Path] = []

    for fp in files:
        try:
            with fp.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            # If unreadable, treat as other
            other.append(fp)
            continue

        if is_screenshot_like(fp.name, data):
            screenshots.append(fp)
        elif is_agent_response(fp.name, data):
            agent_responses.append(fp)
        else:
            other.append(fp)

    return screenshots, agent_responses, other


def copy_grouped(screenshots: List[Path], agent_responses: List[Path], other: List[Path], dest_root: Path) -> None:
    for group_name, group in (
        ("screenshots", screenshots),
        ("agent_responses", agent_responses),
        ("other", other),
    ):
        out_dir = dest_root / group_name
        out_dir.mkdir(parents=True, exist_ok=True)
        for src in group:
            # Recreate partial directory structure for clarity
            relative = src.parent.name + "_" + src.name
            dst = out_dir / relative
            shutil.copy2(src, dst)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify trajectory JSON logs into screenshots, agent_responses, other")
    parser.add_argument(
        "--root",
        default=str(Path(__file__).parent / "trajectories"),
        help="Root trajectories directory (default: ./trajectories)",
    )
    parser.add_argument(
        "--copy-to",
        default=None,
        help="If set, copy grouped files into this directory (creates screenshots/ agent_responses/ other/)",
    )
    args = parser.parse_args()

    root = Path(args.root)
    if not root.exists():
        print(f"Root not found: {root}")
        return

    files = collect_json_files(root)
    screenshots, agent_responses, other = classify_files(files)

    print("\n=== Classification Summary ===")
    print(f"Screenshots-like JSON: {len(screenshots)}")
    print(f"Agent responses:       {len(agent_responses)}")
    print(f"Other:                 {len(other)}\n")

    def preview(label: str, paths: List[Path]) -> None:
        print(f"{label} (showing up to 10):")
        for p in paths[:10]:
            print(f" - {p}")
        if len(paths) > 10:
            print(f" ... (+{len(paths) - 10} more)")
        print()

    preview("Screenshots-like", screenshots)
    preview("Agent responses", agent_responses)
    preview("Other", other)

    if args.copy_to:
        dest_root = Path(args.copy_to)
        dest_root.mkdir(parents=True, exist_ok=True)
        copy_grouped(screenshots, agent_responses, other, dest_root)
        print(f"Copied grouped files into: {dest_root}")


if __name__ == "__main__":
    main()

