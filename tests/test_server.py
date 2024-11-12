# tests/test_server.py

import unittest
import io
import os
import base64
import requests
import warnings
import subprocess
import time
import logging
import webbrowser
from astropy.io import fits
from astropy.io.fits import Header
from PIL import Image
from astropy.utils.exceptions import AstropyDeprecationWarning
from astropy.io.fits.verify import VerifyWarning

# Variable to control whether to open the browser
OPEN_BROWSER = False

class FitsPreviewServerTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Start the server once for all tests."""
        logging.basicConfig(level=logging.INFO)
        logging.info("Starting server...")
        try:
            # Start the server
            cls.server_process = subprocess.Popen(
                ['python', 'fits_preview_server/server.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            cls._ensure_server_running()
        except Exception as e:
            logging.error(f"Failed to start server: {e}")
            raise

    @classmethod
    def _ensure_server_running(cls, retries=30, delay=2):
        """Ensure the server is running by performing a health check with retries."""
        health_url = 'http://127.0.0.1:5000/health'
        for i in range(retries):
            try:
                response = requests.get(health_url)
                if response.status_code == 200:
                    logging.info("Server health check PASSED.")
                    return
            except requests.ConnectionError as e:
                logging.warning(f"Server not running yet (attempt {i+1}/{retries}): {e}")
                time.sleep(delay)

        # If the server fails to start, capture and log stdout and stderr
        stdout, stderr = cls.server_process.communicate()
        logging.error(f"Server stdout: {stdout.decode()}")
        logging.error(f"Server stderr: {stderr.decode()}")
        raise RuntimeError("Server failed to start after initiating the start script.")

    @classmethod
    def tearDownClass(cls):
        """Stop the server after all tests."""
        if hasattr(cls, 'server_process'):
            cls.server_process.terminate()
            cls.server_process.wait()
        logging.info("Server process terminated.")

    def _generate_dummy_fits(self):
        """Generate a dummy FITS file with EXTNAMEs."""
        data = io.BytesIO()
        primary_header = Header({'EXTNAME': 'PRIMARY'})
        secondary_header = Header({'EXTNAME': 'COMPRESSED_IMAGE'})

        with fits.HDUList([fits.PrimaryHDU(data=[[1, 2], [3, 4]], header=primary_header),
                           fits.ImageHDU(data=[[5, 6], [7, 8]], header=secondary_header)]) as hdul:
            hdul.writeto(data)
        data.seek(0)
        return data

    def test_health_check(self):
        """Test the health check endpoint."""
        response = requests.get('http://127.0.0.1:5000/health')
        self.assertEqual(response.status_code, 200)
        self.assertIn("Server is running", response.json()["status"])
        logging.info("Health check test PASSED.")

    def test_preview_fits_with_extname(self):
        """Test preview generation for a dummy FITS file with EXTNAME."""
        data = self._generate_dummy_fits()
        response = requests.post(
            'http://127.0.0.1:5000/preview',
            files={'file': ('test.fits', data.getvalue())},
            data={'extname': 'PRIMARY'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('image_base64', response.json())
        logging.info("Preview FITS with EXTNAME test PASSED.")

    def test_preview_no_file(self):
        """Test the response when no file is provided."""
        response = requests.post('http://127.0.0.1:5000/preview')
        self.assertEqual(response.status_code, 400)
        self.assertIn('File and EXTNAME are required', response.text)
        logging.info("Preview no file test PASSED.")

    def test_preview_invalid_file(self):
        """Test the response for an invalid file."""
        data = io.BytesIO(b"This is not a FITS file")
        response = requests.post(
            'http://127.0.0.1:5000/preview',
            files={'file': ('invalid.txt', data.getvalue())},
            data={'extname': 'PRIMARY'}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        logging.info("Preview invalid file test PASSED.")

    def test_combined_real_fits_preview(self):
        """Test preview generation and rendered preview for a real FITS file with a dynamically chosen EXTNAME."""
        fits_file_path = 'tests/AIA20130101_0000_0171.fits'
        list_extnames_url = 'http://127.0.0.1:5000/list_extnames'

        # First, get the list of EXTNAMEs from the FITS file
        with open(fits_file_path, 'rb') as fits_file:
            response = requests.post(list_extnames_url, files={'file': ('AIA20130101_0000_0171.fits', fits_file)})
            response.raise_for_status()
            extnames = response.json().get("extnames", [])
            if not extnames:
                self.skipTest("No EXTNAMEs found in FITS file")
            else:
                logging.info(f"Extnames found: {extnames}")

        # Use the last EXTNAME for testing
        extname = extnames[-1]

        # Now, request a preview for the selected EXTNAME
        with open(fits_file_path, 'rb') as fits_file:
            response = requests.post(
                'http://127.0.0.1:5000/preview',
                files={'file': ('AIA20130101_0000_0171.fits', fits_file)},
                data={'extname': extname}
            )
            response.raise_for_status()

        # Ensure response contains the base64-encoded image
        response_data = response.json()
        self.assertIn('image_base64', response_data)

        # Decode and verify the image data
        image_data = base64.b64decode(response_data['image_base64'])
        with Image.open(io.BytesIO(image_data)) as img:
            img.verify()

        logging.info(f"Real FITS file preview test PASSED for EXTNAME: {extname}")

        # Now, test the rendered preview
        if OPEN_BROWSER:
            preview_url = f'http://127.0.0.1:5000/preview_rendered?file={fits_file_path}&extname={extname}'
            webbrowser.open(preview_url)
            logging.info(f"Opened browser to {preview_url}")

if __name__ == '__main__':
    warnings.simplefilter("ignore", ResourceWarning)
    unittest.main()