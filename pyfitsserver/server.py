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
import astropy.units as u
try:
    from color_tables import aia_color_table, aia_wave_dict
except ModuleNotFoundError:
    from pyfitsserver.color_tables import aia_color_table, aia_wave_dict

aia_channels = [str(int(key.value)) for key in aia_wave_dict.keys()]

mpl_use('Agg')  # Non-interactive backend for Matplotlib

app = Flask("pyFitsServer")

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

the_norm = "rankdata"

def process_fits_hdu(hdu):
    """Process and normalize the FITS HDU data."""
    im = hdu.data.astype(np.float32)
    if im is None:
        raise ValueError("HDU data is None")
    if np.isnan(im).sum() / np.isfinite(im).sum() > 1.0:
        raise ValueError("HDU data contains more than 50% NaNs")
    the_mean = np.nanmean(im)
    the_std = np.nanstd(im)
    im -= the_mean
    im /= 0.25 * the_std
    the_min, the_max = 1.05 * np.nanmin(im), np.nanmax(im)
    im_normalized = (im - the_min) / (the_max-the_min + 1e-5)
    return np.log10(im_normalized + 1e-5)

def generate_image_base64(data, cmap="viridis"):
    """Generate a base64-encoded PNG image from the normalized FITS data with the specified color map."""
    fig, ax = plt.subplots()
    data = np.squeeze(data)
    from scipy.stats import rankdata

    shp = data.shape
    data = rankdata(data.flatten()) / len(data.flatten())
    data = data.reshape(*shp)
    print(data.shape)
    mean, std = np.nanmean(data), np.nanstd(data)

    ax.imshow(data, origin="lower", cmap=cmap, vmin=0, vmax=1) # , vmin=mean-2*std, vmax=mean+2*std)
    ax.axis('off')
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', bbox_inches='tight', pad_inches=0)
    plt.close(fig)
    img_buffer.seek(0)
    return base64.b64encode(img_buffer.getvalue()).decode('utf-8')

def get_wavelength(file, hdul):
    wave = [int(wv) for wv in aia_channels if wv in file.filename]
    cmap = aia_color_table(wave[0] * u.angstrom) if wave else "gray"
    return wave, cmap


def get_fits_hdu_and_cmap(file, extname="compressed"):

    file.seek(0)

    with fits.open(io.BytesIO(file.read())) as hdul:
        extnames = [h.header.get('EXTNAME', "PRIMARY") for h in hdul if h.data is not None]
        wave, cmap = get_wavelength(file, hdul)

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

# Load the static parts from the template
def load_template(template_path):
    with open(template_path, 'r') as file:
        return file.read()

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

        # Load the static template from an HTML file
        try:
            template_content = load_template("fits_preview_server/template.html")
        except:
            template_content = load_template("template.html")

        # Generate the dynamic body content
        body_content = f"""
        <body>
            <img id="image" src="data:image/png;base64,{image_base64}" alt="FITS Image">
            <h2>Frame: {framename}, Shape: {im_normalized.shape}, Norm: {the_norm}</h2>
            <h3>HDUList: {[nme for nme in extnames]}</h3>
        </body>
        </html>
        """

        # Combine static template with dynamic content
        html_content = template_content + body_content

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

def main():
    """Main entry point for starting the server."""
    app.run(host='127.0.0.1', port=5000, debug=True)

if __name__ == "__main__":
    main()
