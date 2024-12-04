import subprocess
import sys
import logging
import os
from importlib.resources import files
import requests
import platform
import shutil
from pathlib import Path

# Constants
VSIX_URL = "https://github.com/GillySpace27/pyFitsServer/releases/download/v0.0.26/pyfitsvsc-0.0.4.vsix"
LOCAL_VSIX_PATH = "pyfitsserver/lib/pyfitsvsc-0.0.4.vsix"
VSIX_FILENAME = "pyfitsvsc-0.0.4.vsix"

def is_vscode_installed():
    try:
        # Check if VSCode is installed by running 'code --version'
        subprocess.run(["code", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def prompt_user(question):
    """ Prompt the user with a yes/no question and return True if the answer is yes. """
    while True:
        response = input(f"{question} (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print("Please respond with 'y' or 'n'.")

def download_file(url, output_path):
    """ Download a file from a URL and save it to the specified local path. """
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
    logging.info(f"Downloaded {url} to {output_path}")

def install_vscode():
    os_name = platform.system()
    try:
        if os_name == "Linux":
            download_url = "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64"
            output_path = "/tmp/vscode.deb"
            download_file(download_url, output_path)
            subprocess.run(["sudo", "dpkg", "-i", output_path], check=True)
        elif os_name == "Darwin":
            download_url = "https://code.visualstudio.com/sha/download?build=stable&os=darwin-universal"
            output_path = "/tmp/vscode.dmg"
            download_file(download_url, output_path)
            subprocess.run(["hdiutil", "attach", output_path], check=True)
            subprocess.run(["/Volumes/Visual Studio Code/Install Visual Studio Code.app/Contents/MacOS/Electron"], check=True)
            subprocess.run(["hdiutil", "detach", "/Volumes/Visual Studio Code"], check=True)
        elif os_name == "Windows":
            download_url = "https://code.visualstudio.com/sha/download?build=stable&os=win32-x64-user"
            output_path = str(Path.home() / "Downloads" / "VSCodeSetup.exe")
            download_file(download_url, output_path)
            subprocess.run([output_path, "/silent", "/mergetasks=!runcode"], check=True)
        else:
            logging.error(f"Unsupported OS {os_name}")
            return False
        logging.info("VSCode installation completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"VSCode installation failed: {e}")
        return False

def download_vscode_extension():
    """ Downloads the VSIX extension file. """
    os.makedirs(os.path.dirname(LOCAL_VSIX_PATH), exist_ok=True)
    logging.info(f"Downloading {VSIX_URL}")
    try:
        with requests.get(VSIX_URL, stream=True) as r:
            r.raise_for_status()
            with open(LOCAL_VSIX_PATH, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logging.info(f"Downloaded to {LOCAL_VSIX_PATH}")
    except Exception as e:
        logging.error(f"Failed to download VSIX file: {e}")
        sys.exit(1)

def install_vscode_extension():
    try:
        # Locate the .vsix file in the package
        vsix_path = files("pyfitsserver.lib").joinpath(VSIX_FILENAME)

        # Check if the file exists, if not download it
        if not vsix_path.exists():
            logging.info(f"VSIX file not found at: {vsix_path}, attempting to download...")
            download_vscode_extension()

        # Re-check after download attempt
        if not vsix_path.exists():
            logging.error(f"VSCode extension file still not found at: {vsix_path}")
            sys.exit(1)

        # Check if VSCode is installed
        if not is_vscode_installed():
            logging.error("VSCode is not installed.")
            if prompt_user("Would you like to install VSCode now?"):
                if not install_vscode():
                    logging.error("VSCode installation was unsuccessful.")
                    sys.exit(1)
            else:
                logging.error("VSCode installation is required to proceed.")
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
