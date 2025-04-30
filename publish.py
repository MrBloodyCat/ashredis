import os
import subprocess

from dotenv import load_dotenv


def tests():
    """Start tests scripts."""
    subprocess.run(["python", "-m", "unittest", "discover", "-s", "tests"], check=True)


def clean():
    """Removes old builds."""
    if os.path.exists("dist"):
        for file in os.listdir("dist"):
            os.remove(f"dist/{file}")


def build():
    """Picking up the package."""
    subprocess.run(["python", "-m", "build"], check=True)


def upload():
    """Uploads to PyPI with a token."""
    load_dotenv()
    token = os.getenv("PYPI_TOKEN")
    if not token:
        raise ValueError("PYPI_TOKEN is not installed!")
    subprocess.run([
        "twine", "upload",
        "--username", "__token__",
        "--password", token,
        "dist/*"
    ], check=True)


if __name__ == "__main__":
    print("[LOG] Start tests")
    tests()
    print("[LOG] Cleaning up old builds")
    clean()
    print("[LOG] Assembling the package")
    build()
    print("[LOG] Uploading to PyPI")
    try:
        upload()
    except subprocess.CalledProcessError as e:
        print("[LOG] Try increasing the version in pyproject.toml")
    else:
        print("[LOG]Successfully published!")
