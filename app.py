from flask import Flask, request, render_template, send_from_directory, redirect, url_for, jsonify
import subprocess
import os
import time

app = Flask(__name__)

# Define a route for Server-Sent Events (SSE)
@app.route('/stream-data/<script_choice>/<keyword>/<num_products>')
def stream_data(script_choice, keyword, num_products):
    def generate():
        # Simulate sending data from the scraping process
        for i in range(int(num_products)):
            time.sleep(1)  # Simulate a delay in data processing
            yield f"data: Product {i + 1} for '{keyword}' using '{script_choice}'\n\n"  # Send product data as SSE

    return app.response_class(generate(), mimetype='text/event-stream')

# Define routes
@app.route('/')
def index():
    return render_template('index.html')

# Route to run the selected script
@app.route('/run-script', methods=['POST'])
def run_script():
    try:
        # Get form data
        script_choice = request.form['script']
        keyword = request.form['keyword']
        num_products = request.form['num_products']

        print(f"Received script: {script_choice}, keyword: {keyword}, num_products: {num_products}")  # Debugging line

        # Set the output filename based on the selected script
        if script_choice == 'scraper_1':
            output_file = 'scraped_products_uniformadvantage.xlsx'
            subprocess.run(['python', 'www.uniformadvantage.py', keyword, num_products], check=True)
        elif script_choice == 'scraper_2':
            output_file = 'scraped_products_wearfigs.xlsx'
            subprocess.run(['python', 'WearFigs.py', keyword, num_products], check=True)
        elif script_choice == 'scraper_3':
            output_file = 'scraped_products_scrubharvard.xlsx'
            subprocess.run(['python', 'scrubharvard.py', keyword, num_products], check=True)

        print(f"Scraping complete. Data saved to '{output_file}'.")  # Debugging line

        # Send a JSON response back to the client with the stream URL
        return jsonify({"success": True, "stream_url": url_for('stream_data', script_choice=script_choice, keyword=keyword, num_products=num_products)})

    except Exception as e:
        print(f"Error running script: {e}")  # Debugging line
        return jsonify({"success": False, "error": str(e)})

# Route to download the scraped file
@app.route('/download/<filename>')
def download_file(filename):
    # Make sure the directory is correct and the file exists
    directory = os.path.join(app.root_path, 'static')  # Ensure 'static' folder has the files
    return send_from_directory(directory, filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1111, debug=True)
