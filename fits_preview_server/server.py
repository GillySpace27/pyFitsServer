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

mpl_use('Agg')  # Non-interactive backend for Matplotlib

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
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
    nanperc = np.sum(np.isnan(im)) / im.size
    if nanperc > 0.8:
        raise ValueError(f"HDU data is {nanperc * 100:.2f}% NaNs")

    # Log data statistics for debugging
    logger.info(f"Image shape: {im.shape}, dtype: {im.dtype}, min: {np.nanmin(im)}, max: {np.nanmax(im)}")

    # Normalize and apply a log transform for visibility
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

    image_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
    return image_base64

def get_fits_hdu_and_cmap(file, extname):
    """Retrieve the HDU with the specified EXTNAME and determine the colormap."""
    try:
        # Use regex to find the wavelength in the filename if it's structured like "_####.fits"
        match = re.search(r"_(\d{3,4})\.fits", file.filename)
        if match:
            wave = int(match.group(1))
            cmap = aia_color_table(wave * u.angstrom)
            logger.info(f"Parsed wavelength: {wave} Å - Colormap applied.")
        else:
            logger.warning("Wavelength not found in filename; using default colormap.")
            wave = None
            cmap = "plasma"  # Default colormap if parsing fails

        # Read and validate HDU
        file.seek(0)  # Ensure we're at the start of the file
        with fits.open(io.BytesIO(file.read())) as hdul:
            hdu = next((h for h in hdul if h.header.get('EXTNAME') == extname), None)
            if hdu is None or hdu.data is None:
                raise ValueError("Selected EXTNAME not found or has no data.")

    except Exception as e:
        raise ValueError("Error reading FITS file or EXTNAME") from e

    return hdu, cmap, wave  # Return wave for further use if needed

def validate_file_and_extname(file, extname):
    """Validate the presence and type of the file and extname."""
    if not file or not extname:
        logger.error("File and EXTNAME are required.")
        raise ValueError("File and EXTNAME are required")

    if file.filename == '':
        logger.error("No selected file")
        raise ValueError("No selected file")

    if not file.filename.endswith('.fits'):
        logger.error("Invalid file type. Only FITS files are accepted.")
        raise ValueError("Invalid file type. Only FITS files are accepted.")

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

        # Add logging to check file and extname presence
        if not file:
            logger.error("File parameter is missing in request.")
            return jsonify({"error": "File and EXTNAME are required"}), 400

        if not extname:
            logger.error("EXTNAME parameter is missing in request.")
            return jsonify({"error": "File and EXTNAME are required"}), 400

        logger.info(f"Received file: {file.filename}")

        hdu, cmap, wave = get_fits_hdu_and_cmap(file, extname)
        im_normalized = process_fits_hdu(hdu)
        image_base64 = generate_image_base64(im_normalized, cmap)

        return jsonify({"status": "Preview generated", "image_base64": image_base64}), 200

    except ValueError as e:
        logger.error(f"ValueError in /preview: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in /preview: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/preview_rendered', methods=['POST', 'GET'])
def preview_rendered():
    """Endpoint to generate and display a preview image for a selected EXTNAME in a web browser."""
    try:
        # Handle POST requests with file upload
        if request.method == 'POST':
            file = request.files.get('file')
            extname = request.form.get('extname')

        # Handle GET requests with file path and extname in query parameters
        elif request.method == 'GET':
            file_path = request.args.get('file')  # Expect file path in query parameter
            extname = request.args.get('extname')
            if not file_path:
                raise ValueError("File parameter is missing in GET request.")
            if not extname:
                raise ValueError("EXTNAME parameter is missing in GET request.")

            # Open file from the provided path for GET requests
            with open(file_path, 'rb') as f:
                file = io.BytesIO(f.read())
                file.filename = os.path.basename(file_path)

        # Ensure file and extname are valid
        validate_file_and_extname(file, extname)
        logger.info(f"Processing file: {file.filename}")

        hdu, cmap, wave = get_fits_hdu_and_cmap(file, extname)
        im_normalized = process_fits_hdu(hdu)
        image_base64 = generate_image_base64(im_normalized, cmap)

        html_content = f"""
        <html>
        <head>
            <title>FITS Preview</title>
        </head>
        <body>
            <h1>FITS Image Preview: Wavelength {wave if wave else 'N/A'}</h1>
            <img src="data:image/png;base64,{image_base64}" alt="FITS Image">
        </body>
        </html>
        """
        return html_content, 200

    except ValueError as e:
        logger.error(f"ValueError in /preview_rendered: {str(e)}")
        return jsonify({"error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error in /preview_rendered: {str(e)}")
        logger.error(traceback.format_exc())  # Log the full traceback
        return jsonify({"error": "An unexpected error occurred"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify server status."""
    uptime = time() - start_time
    logger.info(f"Health check requested - Server uptime: {uptime:.2f} seconds")
    return jsonify({"status": f"Server is running, uptime {uptime:.2f} seconds"}), 200

@app.route('/list_extnames', methods=['POST'])
def list_extnames():
    """Endpoint to list all EXTNAMEs in a FITS file."""
    try:
        file = request.files.get('file')
        if not file:
            raise ValueError("No file provided")

        extnames = []
        file.seek(0)  # Ensure we're at the start of the file
        with fits.open(io.BytesIO(file.read())) as hdul:
            for hdu in hdul:
                extname = hdu.header.get('EXTNAME')
                if extname:
                    extnames.append(extname)
                    logger.info(f"Found EXTNAME: {extname}")

        return jsonify({"extnames": extnames}), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return handle_error(e)

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)