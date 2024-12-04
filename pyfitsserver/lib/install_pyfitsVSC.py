import subprocess
import sys
import logging
import os
from importlib.resources import files
import requests

url = "https://github.com/GillySpace27/pyFitsServer/releases/download/v0.0.26/pyfitsvsc-0.0.4.vsix"
local_filename = "pyfitsserver/lib/pyfitsvsc-0.0.4.vsix"
vsix_filename = "pyfitsvsc-0.0.4.vsix"

def is_vscode_installed():
    try:
        # Check if VSCode is installed by running 'code --version'
        subprocess.run(["code", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def download_vscode_extension():

    # Ensure the directory exists
    os.makedirs(os.path.dirname(local_filename), exist_ok=True)

    logging.info(f"Downloading {url}")
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logging.info(f"Downloaded to {local_filename}")
    except Exception as e:
        logging.error(f"Failed to download VSIX file: {e}")
        sys.exit(1)

def install_vscode_extension():

    # Check if VSCode is installed
    if not is_vscode_installed():
        logging.error("VSCode is not installed. Please install VSCode first.")
        sys.exit(1)

    try:
        # Locate the .vsix file in the package
        vsix_path = files("pyfitsserver.lib").joinpath(vsix_filename)

        # Check if the file exists, if not download it
        if not vsix_path.exists():
            logging.info(f"VSIX file not found at: {vsix_path}, attempting to download...")
            download_vscode_extension()

        # Re-check after download attempt
        if not vsix_path.exists():
            logging.error(f"VSCode extension file still not found at: {vsix_path}")
            sys.exit(1)


        # Try to install the extension using the VSCode CLI
        logging.info(f"Attempting to install VSCode extension from {vsix_path}")
        subprocess.run(["code", "--install-extension", str(vsix_path)], check=True)
        logging.info("VSCode extension installed successfully!")
    except subprocess.CalledProcessError as e:
        logging.error(f"Automatic installation failed: {e}")
        logging.info("Falling back to opening VSCode with the extension visible.")

        try:
            # Attempt to open VSCode with the folder of the extension
            subprocess.run(["code", "--folder-uri", os.path.dirname(vsix_path)], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to open VSCode: {e}")
            logging.info("Please install the extension manually:")
            logging.info(f"  code --install-extension {vsix_path}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    install_vscode_extension()
