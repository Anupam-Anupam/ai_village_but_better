import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any


def _validate_agent_response_schema(data: Dict[str, Any]) -> bool:
    """Validate that data matches expected agent response schema."""
    if not isinstance(data, dict):
        return False
    
    # Schema 1: response.output structure
    if "response" in data:
        response = data["response"]
        if isinstance(response, dict) and "output" in response:
            output = response["output"]
            if isinstance(output, list):
                for item in output:
                    if isinstance(item, dict) and item.get("type") == "message":
                        content = item.get("content", [])
                        if isinstance(content, list) and content:
                            return True
    
    # Schema 2: direct output structure
    if "output" in data:
        output = data["output"]
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict) and item.get("type") == "message":
                    content = item.get("content", [])
                    if isinstance(content, list) and content:
                        return True
    
    # Schema 3: role-based messages
    if "role" in data and data.get("role") == "assistant":
        return True
    
    return False


def is_agent_response(filename: str, data: Dict) -> bool:
    """Check if a file is an agent response with schema validation."""
    if not isinstance(filename, str) or not isinstance(data, dict):
        return False
    
    name = filename.lower()
    if "agent_response" in name or "agent-response" in name:
        return True
    
    return _validate_agent_response_schema(data)


def extract_agent_response_text(data: Dict[str, Any]) -> Optional[str]:
    """Extract text content from an agent response JSON with schema validation."""
    if not isinstance(data, dict):
        return None
    
    # Schema 1: response.output structure
    if "response" in data:
        response = data["response"]
        if isinstance(response, dict) and "output" in response:
            output = response["output"]
            if isinstance(output, list):
                for item in output:
                    if isinstance(item, dict) and item.get("type") == "message":
                        content = item.get("content", [])
                        if isinstance(content, list):
                            for content_item in content:
                                if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                    text = content_item.get("text")
                                    if isinstance(text, str) and text:
                                        return text
    
    # Schema 2: direct output structure
    if "output" in data:
        output = data["output"]
        if isinstance(output, list):
            for item in output:
                if isinstance(item, dict) and item.get("type") == "message":
                    content = item.get("content", [])
                    if isinstance(content, list):
                        for content_item in content:
                            if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                                text = content_item.get("text")
                                if isinstance(text, str) and text:
                                    return text
    
    return None


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

