# fits_preview_server/server.py

from flask import Flask, request, jsonify
import numpy as np
from astropy.io import fits
import matplotlib.pyplot as plt
from matplotlib import use as mpl_use
import io
import os
import logging
import traceback
from time import time
import base64
import re
import astropy.units as u
from color_tables import aia_color_table
from warnings import warn

mpl_use('Agg')  # Non-interactive backend for Matplotlib

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - \n\t\t\t%(message)s\n',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Start time to track uptime
start_time = time()

def process_fits_hdu(hdu):
    """Process and normalize the FITS HDU data."""
    im = hdu.data
    if im is None:
        raise ValueError("HDU data is None")
    try:
        if np.sum(np.isnan(im)) / np.sum(np.isfinite(im)) > 1.0:
            raise ValueError("HDU data contains more than 50% NaNs")
    except Exception as e:
        raise ValueError(f"Failed to load HDU: {e}")
    # logger.info(f"Image shape: {im.shape}, dtype: {im.dtype}, min: {np.nanmin(im)}, max: {np.nanmax(im)}")
    im_normalized = (im - np.nanmin(im)) / (np.nanmax(im) - np.nanmin(im) + 1e-5)  # Avoid division by zero
    return np.log10(im_normalized + 1)  # +1 to avoid log(0)

def generate_image_base64(data, cmap="viridis"):
    """Generate a base64-encoded PNG image from the normalized FITS data with the specified color map."""
    fig, ax = plt.subplots()
    ax.imshow(data, origin="lower", cmap=cmap)
    ax.axis('off')

    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    img_buffer.seek(0)

    return base64.b64encode(img_buffer.getvalue()).decode('utf-8')

def get_fits_hdu_and_cmap(file, extname="compressed"):
    # Match the wavelength in the filename
    match = re.search(r"_(\d{3,4})\.fits", file.filename)
    wave = int(match.group(1)) if match else None
    cmap = aia_color_table(wave * u.angstrom) if wave else "plasma"

    file.seek(0)
    extnames = []

    with fits.open(io.BytesIO(file.read())) as hdul:
        for hdu in hdul:
            extname_header = hdu.header.get('EXTNAME')
            if extname_header:
                extnames.append(extname_header)
            if extname_header == extname:
                if hdu.data is not None:
                    return hdu.data, cmap, wave, extnames
                else:
                    raise ValueError(f"Selected EXTNAME '{extname}' has no data.")

        if is_int(extname[-1]):
            hdu = hdul[extnames[int(extname)]]
            if hdu and hdu.data is not None:
                return hdu.data, cmap, wave, extnames
            else:
                raise ValueError("The last HDU has no data.")

        raise ValueError(f"Selected EXTNAME '{extname}' not found. Names in file: {extnames}")

def is_int(variable):
    # Check if the variable is an integer
    if isinstance(variable, int):
        return True
    # Check if the variable is a string that represents an integer
    elif isinstance(variable, str) and variable.isdigit():
        return True
    else:
        return False


def validate_file_and_extname(file, extname):
    """Validate the presence and type of the file and extname."""
    if not (file and extname and file.filename.endswith('.fits')):
        raise ValueError("File and EXTNAME are required, and file must be a FITS file")

def handle_error(e):
    """Handle errors by logging the stack trace and returning a JSON response."""
    logger.error(f"Error: {str(e)}")
    logger.error(traceback.format_exc())
    return jsonify({"error": str(e)}), 500

@app.route('/preview', methods=['POST'])
def preview():
    try:
        file = request.files.get('file')
        extname = request.form.get('extname')
        validate_file_and_extname(file, extname)

        try:
            hdu, cmap, wave, extnames = get_fits_hdu_and_cmap(file, extname)
        except FileNotFoundError:
            hdu, cmap, wave, extnames = get_fits_hdu_and_cmap(file, -1)

        im_normalized = process_fits_hdu(hdu)
        image_base64 = generate_image_base64(im_normalized, cmap)

        return jsonify({"status": "Preview generated", "image_base64": image_base64}), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return handle_error(e)

@app.route('/preview_rendered', methods=['POST', 'GET'])
def preview_rendered():
    try:
        if request.method == 'POST':
            file = request.files.get('file')
            extname = request.form.get('extname')
        else:
            file_path = request.args.get('file')
            extname = request.args.get('extname')
            if not file_path:
                raise ValueError("File parameter is missing")
            with open(file_path, 'rb') as f:
                file = io.BytesIO(f.read())
                file.filename = os.path.basename(file_path)

        validate_file_and_extname(file, extname)
        hdu, cmap, wave, extnames = get_fits_hdu_and_cmap(file, extname)

        # if is_int(extname):
        #     extname = extnames[extname]

        im_normalized = process_fits_hdu(hdu)
        image_base64 = generate_image_base64(im_normalized, cmap)
        html_content = f"""
        <html>
        <head>
            <title>FITS Preview</title>
        </head>
        <body>
            <img src="data:image/png;base64,{image_base64}" alt="FITS Image">
            <h2>Frame: {extname if extname else 'N/A'}, Shape: {im_normalized.shape}</h2>
            <h3>List: {[nme for nme in extnames]} </h3>
        </body>
        </html>
        """
        return html_content, 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return handle_error(e)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify server status."""
    uptime = time() - start_time
    return jsonify({"status": f"Server is running, uptime {uptime:.2f} seconds"}), 200

@app.route('/list_extnames', methods=['POST', 'GET'])
def list_extnames():
    try:
        if request.method == 'POST':
            file = request.files.get('file')
            file_data = io.BytesIO(file.read())
        else:
            file_path = request.args.get('file')
            if not file_path:
                raise ValueError("File parameter is missing")
            with open(file_path, 'rb') as f:
                file_data = io.BytesIO(f.read())

        extnames = []
        file_data.seek(0)
        with fits.open(file_data) as hdul:
            extnames = [h.header.get('EXTNAME') for h in hdul if h.header.get('EXTNAME')]

        return jsonify({"extnames": extnames}), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return handle_error(e)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
