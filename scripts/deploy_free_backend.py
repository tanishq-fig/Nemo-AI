import argparse
import os
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi


def build_backend_bundle(source_dir: Path, out_dir: Path) -> None:
    ignore_names = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
        "cache",
        "data",
        "results.txt",
        "MEGA_TEST_REPORT.md",
        "mega_test.py",
        "test_platform_thorough.py",
    }

    out_dir.mkdir(parents=True, exist_ok=True)

    for item in source_dir.iterdir():
        if item.name in ignore_names:
            continue
        target = out_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)

    dockerfile_free = out_dir / "Dockerfile.free"
    if dockerfile_free.exists():
        shutil.copy2(dockerfile_free, out_dir / "Dockerfile")

    req_free = out_dir / "requirements_free.txt"
    if req_free.exists():
        shutil.copy2(req_free, out_dir / "requirements.txt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy backend to Hugging Face Space (Docker SDK)")
    parser.add_argument("--space-id", required=True, help="Hugging Face Space id, e.g. username/argo-backend")
    parser.add_argument("--source-dir", default="backend", help="Backend source directory")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")

    source_dir = Path(args.source_dir).resolve()
    if not source_dir.exists():
        print(f"Source directory not found: {source_dir}")
        return 1

    api = HfApi(token=token)
    api.create_repo(
        repo_id=args.space_id,
        repo_type="space",
        space_sdk="docker",
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory() as tmp:
        bundle_dir = Path(tmp) / "space"
        build_backend_bundle(source_dir, bundle_dir)
        api.upload_folder(
            repo_id=args.space_id,
            repo_type="space",
            folder_path=str(bundle_dir),
            commit_message="Deploy backend from Nemo-AI",
        )

    print(f"Backend uploaded to https://huggingface.co/spaces/{args.space_id}")
    print(f"Backend URL: https://{args.space_id.replace('/', '-')}.hf.space")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
