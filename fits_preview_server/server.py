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
    format='%(asctime)s - %(levelname)s - \n\t\t\t%(message)s\n',
    handlers=[
        logging.FileHandler("server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

start_time = time()

def process_fits_hdu(hdu):
    """Process and normalize the FITS HDU data."""
    im = hdu.data
    if im is None:
        raise ValueError("HDU data is None")
    if np.isnan(im).sum() / np.isfinite(im).sum() > 1.0:
        raise ValueError("HDU data contains more than 50% NaNs")
    im_normalized = (im - np.nanmin(im)) / (np.nanmax(im) - np.nanmin(im) + 1e-5)
    return np.log10(im_normalized + 1)

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
    match = re.search(r"_(\d{3,4})\.fits", file.filename)
    wave = int(match.group(1)) if match else None
    cmap = aia_color_table(wave * u.angstrom) if wave else "plasma"
    file.seek(0)

    with fits.open(io.BytesIO(file.read())) as hdul:
        extnames = [h.header.get('EXTNAME') for h in hdul if h.header.get('EXTNAME')]

        try:
            if extname.isdigit() or (extname.startswith('-') and extname[1:].isdigit()):
                index = int(extname)
                hdu = hdul[index]
                if hdu.data is not None:
                    return hdu, cmap, wave, extnames, extnames[int(extname)]
            else:
                for hdu in hdul:
                    if hdu.header.get('EXTNAME') == extname and hdu.data is not None:
                        return hdu, cmap, wave, extnames, extname
        except IndexError:
            raise ValueError(f"Index {extname} is out of range for the HDU list. Available extnames: {extnames}")

        raise ValueError(f"Selected EXTNAME '{extname}' not found or has no data. Available extnames: {extnames}")


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
async def preview():
    try:
        file = request.files.get('file')
        extname = request.form.get('extname')
        validate_file_and_extname(file, extname)
        hdu, cmap, wave, extnames, framename = get_fits_hdu_and_cmap(file, extname)
        im_normalized = process_fits_hdu(hdu)
        image_base64 = generate_image_base64(im_normalized, cmap)
        return jsonify({"status": "Preview generated", "image_base64": image_base64}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return handle_error(e)

@app.route('/preview_rendered', methods=['POST', 'GET'])
async def preview_rendered():
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
        hdu, cmap, wave, extnames, framename = get_fits_hdu_and_cmap(file, extname)
        im_normalized = process_fits_hdu(hdu)
        image_base64 = generate_image_base64(im_normalized, cmap)
        html_content = f"""
<html>
<head>
    <title>FITS Preview</title>
    <style>
        body {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 0;
            height: 100vh;
            background-color: #909090;
            font-family: Arial, sans-serif;
        }}

        #img-container {{
            border: 1px solid black;
            overflow: hidden;
            width: 95%;
            height: 95%;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            # object-fit: contain;
        }}

        img {{
            # max-width: 100%;
            max-height: 100%;
            height: auto;
            width: 100%;
            object-fit: contain;
            image-rendering: pixelated; /* Ensures discrete square pixels */
        }}

        img:active {{
            # cursor: zoom-in;
        }}
    </style>
</head>
<body>
    <div id="img-container">
        <img id="image" src="data:image/png;base64,{image_base64}" alt="FITS Image">
    </div>
    <h2>Frame: {framename}, Shape: {im_normalized.shape}</h2>
    <h3>List: {[nme for nme in extnames]}</h3>
</body>
</html>
"""




        return html_content, 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return handle_error(e)

@app.route('/health', methods=['GET'])
async def health_check():
    """Health check endpoint to verify server status."""
    uptime = time() - start_time
    return jsonify({"status": f"Server is running, uptime {uptime:.2f} seconds"}), 200

@app.route('/list_extnames', methods=['POST', 'GET'])
async def list_extnames():
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
