# pyFitsServer

**pyFitsServer** is a lightweight server to facilitate the rendering and previewing of FITS (Flexible Image Transport System) files. It is designed to work in conjunction with the **pyFitsVSC** Visual Studio Code extension, providing backend services to support the frontend visualization capabilities.

## Description

The **pyFitsServer** acts as the backend server for serving FITS file previews. It processes the FITS files and provides the necessary data and/or images to the **pyFitsVSC** extension.

## Prerequisites

To run the **pyFitsServer**, you need to have Python installed on your system. It is recommended to use a virtual environment to manage dependencies.

## Installation

To install and run **pyFitsServer**, follow these steps:

1. **Clone the repository**:
    ```bash
    git clone https://github.com/GillySpace27/pyFitsServer.git
    ```

2. **Navigate to the directory**:
    ```bash
    cd pyFitsServer
    ```

3. **Create a virtual environment (optional but recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

4. **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5. **Run the server**:
    ```bash
    python server.py
    ```

6. **Confirm the server is running properly by running tests (from the project root)**:
    ```bash
    pytest
    ```

If everything is set up correctly, the server should be running and you should see output indicating that it is ready to accept requests.

## Usage

Once the **pyFitsServer** is running, it will be ready to interface with the **pyFitsVSC** extension for Visual Studio Code. The server will handle backend operations, such as rendering and processing the FITS files, and send the necessary data back to the **pyFitsVSC** extension for display.

## Integration with pyFitsVSC

**pyFitsVSC** is a VS Code extension designed to provide previews of FITS files seamlessly within the editor. Here’s how to use it in conjunction with **pyFitsServer**:

1. **Ensure the server is running** by following the [installation steps](#installation).
2. **Install the pyFitsVSC extension** by following these steps in the `pyfitsvsc` repository:
    1. **Clone the repository**:
        ```bash
        git clone https://github.com/GillySpace27/pyfitsvsc.git
        ```
    2. **Navigate to the directory**:
        ```bash
        cd pyfitsvsc
        ```
    3. **Locate the precompiled `.vsix` file in the repository or compile from source (if needed)**:
        - **To install from the precompiled `.vsix` file:**
            - Open VS Code.
            - Go to Extensions view (`Ctrl+Shift+X`).
            - Click the three-dot menu (`...`).
            - Select `Install from VSIX...`.
            - Browse to and select the precompiled `.vsix` file.
        - **To compile and package from source:**
            1. **Install VSCE if not already installed**:
                ```bash
                npm install -g vsce
                ```
            2. **Compile the TypeScript code**:
                ```bash
                npm run compile
                ```
            3. **Package the extension**:
                ```bash
                vsce package
                ```
            4. **Install the VSIX file**:
                - Open VS Code.
                - Go to Extensions view (`Ctrl+Shift+X`).
                - Click the three-dot menu (`...`).
                - Select `Install from VSIX...`.
                - Browse to and select the `.vsix` file created in the previous step.

## Contributing

Contributions are welcome! If you encounter any issues or have suggestions for improvements, please feel free to open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

With these updates, users should have a comprehensive guide to installing, running, and using both `pyFitsServer` and the `pyFitsVSC` extension. If you find these changes satisfactory or if there are any additional details you'd like to include, please let me know.
