import subprocess
import sys
import os
from importlib.resources import files

def install_vscode_extension():
    try:
        # Locate the .vsix file in the package
        vsix_path = files("pyfitsserver").joinpath("pyfitsvsc-0.0.4.vsix")

        # Try to install the extension using the VSCode CLI
        print(f"Attempting to install VSCode extension from {vsix_path}")
        subprocess.run(["code", "--install-extension", str(vsix_path)], check=True)
        print("VSCode extension installed successfully!")
    except Exception as e:
        # Fallback to opening VSCode in the directory of the extension
        print(f"Automatic installation failed: {e}")
        print("Falling back to opening VSCode with the extension visible.")
        try:
            subprocess.run(["code", "--folder-uri", os.path.dirname(vsix_path)], check=True)
        except Exception as e:
            print(f"Failed to open VSCode: {e}")
            print("Please install the extension manually:")
            print(f"  code --install-extension {vsix_path}")