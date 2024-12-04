import subprocess
import io
import os
import logging
import traceback
import pathlib
from time import time
import base64
import numpy as np
import importlib.util
import astropy.units as u
from astropy.io import fits
from flask import Flask, request, jsonify
from matplotlib import pyplot as plt
from matplotlib import use as mpl_use
import importlib.resources as pkg_resources

# Function to dynamically import a module and handle fallback
def dynamic_import(module_name, fallback_name):
    module_spec = importlib.util.find_spec(module_name)
    if module_spec is not None:
        module = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(module)
        return module
    else:
        logging.warning(f"{module_name} not found, trying {fallback_name}...")
        fallback_spec = importlib.util.find_spec(fallback_name)
        if fallback_spec is not None:
            module = importlib.util.module_from_spec(fallback_spec)
            fallback_spec.loader.exec_module(module)
            return module
        else:
            raise ModuleNotFoundError(f"Neither {module_name} nor {fallback_name} could be imported.")

# Try to import the color_tables module
try:
    color_tables = dynamic_import("pyfitsserver.lib.color_tables", "color_tables")
    aia_color_table = color_tables.aia_color_table
    aia_wave_dict = color_tables.aia_wave_dict
except ModuleNotFoundError as e:
    logging.error(f"Failed to import color tables: {e}")
    raise

aia_channels = [str(int(key.value)) for key in aia_wave_dict.keys()]

mpl_use('Agg')  # Non-interactive backend for Matplotlib

app = Flask("pyFitsServer")

def configure_logging():
    """
    Configures the logging settings for the script, setting up both
    file and stream handlers.
    """
    # Get the absolute path to the directory containing the current script
    log_dir = pathlib.Path(__file__).parent.absolute() / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)  # Ensure the log directory exists

    # Define the log file path
    log_file = log_dir / "server.log"

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    return logger

# Call the configure_logging function to set up logging
logger = configure_logging()
logger.info("Logging is configured and ready to use.")

start_time = time()
the_norm = "rankdata"

def process_fits_hdu(hdu):
    """Process and normalize the FITS HDU data."""
    im = hdu.data.astype(np.float32)
    if im is None:
        raise ValueError("HDU data is None")
    if np.isnan(im).sum() / np.isfinite(im).sum() > 0.5:
        raise ValueError("HDU data contains more than 50% NaNs")
    the_mean = np.nanmean(im)
    the_std = np.nanstd(im)
    im -= the_mean
    im /= 0.25 * the_std
    the_min, the_max = 1.05 * np.nanmin(im), np.nanmax(im)
    im_normalized = (im - the_min) / (the_max - the_min + 1e-5)
    return np.log10(im_normalized + 1e-5)

def generate_image_base64(data, cmap="viridis"):
    """Generate a base64-encoded PNG image from the normalized FITS data with the specified color map."""
    fig, ax = plt.subplots()
    data = np.squeeze(data)
    from scipy.stats import rankdata

    shp = data.shape
    data = rankdata(data.flatten()) / len(data.flatten())
    data = data.reshape(*shp)

    ax.imshow(data, origin="lower", cmap=cmap, vmin=0, vmax=1)
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

def load_template(template_name="template.html"):
    """Load the content of the given template from the 'pyfitsserver' package."""
    if "lib" not in template_name:
        # template_name = os.path.join("lib", template_name)
        # print(template_name)
        pass
    try:
        template_content = pkg_resources.read_text('pyfitsserver', template_name)
    except FileNotFoundError:
        try:
            template_content = pkg_resources.read_text(__package__, template_name)
        except FileNotFoundError as fnf_error:
            raise RuntimeError(f"Template {template_name} not found in the specified packages.") from fnf_error
        except Exception as e:
            raise RuntimeError(f"An error occurred while loading template {template_name}.") from e
    except Exception as e:
        raise RuntimeError(f"An error occurred while accessing the template {template_name}.") from e
    return template_content

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
        template_content = load_template("template.html")
        print(template_content)

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
