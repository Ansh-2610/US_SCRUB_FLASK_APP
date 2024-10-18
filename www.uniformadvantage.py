from playwright.sync_api import sync_playwright
import time
import pandas as pd
import sys
import os
import mysql.connector  # For MySQL connection
from datetime import datetime

# Function to log messages with timestamp
def log_message(message):
    """Inserts log messages with a timestamp into the Uniform_Advantage_log table."""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  # Replace with your MySQL password
            database="scrapefly"  # Replace with your database name
        )
        cursor = connection.cursor()
        sql_query = "INSERT INTO Uniform_Advantage_log (log_message, log_timestamp) VALUES (%s, %s)"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(sql_query, (message, timestamp))
        connection.commit()
        print(f"Log: {message}")  # Print log message to console for visibility
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")  # Log database errors to console
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Function to scrape product details from a product page
def scrape_product_details(page):
    try:
        log_message("Extracting product details from product page...")

        style_number = page.query_selector('div.product-number .product-id').inner_text()
        log_message(f"Style Number extracted: {style_number}")

        product_name = page.query_selector('h1.product-name').inner_text()
        log_message(f"Product Name extracted: {product_name}")

        rating = page.query_selector('span.sr-only')
        rating_text = rating.inner_text() if rating else "No rating available"
        log_message(f"Rating extracted: {rating_text}")

        reviews = page.query_selector('span.rating-number')
        reviews_count = reviews.inner_text() if reviews else "No reviews"
        log_message(f"Reviews count extracted: {reviews_count}")

        current_price = page.query_selector('div.product-price-ratings .price .value')
        current_price_value = current_price.inner_text() if current_price else "Price not available"
        log_message(f"Current Price extracted: {current_price_value}")

        strike_through_price = page.query_selector('div.product-price-ratings .strike-through.list .value')
        strike_through_price_value = strike_through_price.inner_text() if strike_through_price else "No original price available"
        log_message(f"Original Price extracted: {strike_through_price_value}")

        fabric_button = page.query_selector('button[data-target="#fabric"]')
        if fabric_button:
            log_message("Clicking on fabric details section...")
            fabric_button.click()
            time.sleep(1)
            fabric_section = page.query_selector('div#fabric .card-body ul')
            fabric_details = fabric_section.inner_text() if fabric_section else "Fabric details not available"
            log_message(f"Fabric Details extracted: {fabric_details}")
        else:
            fabric_details = "Fabric section not found"
            log_message("Fabric section not found")

        fit_button = page.query_selector('button[data-target="#fit-and-size"]')
        if fit_button:
            log_message("Clicking on fit and size section...")
            fit_button.click()
            time.sleep(1)
            fit_and_size_section = page.query_selector('div#fit-and-size .card-body')
            fit_and_size_details = fit_and_size_section.inner_text() if fit_and_size_section else "Fit & size details not available"
            log_message(f"Fit & Size Details extracted: {fit_and_size_details}")
        else:
            fit_and_size_details = "Fit & Size section not found"
            log_message("Fit & Size section not found")

        return {
            "Style Number": style_number,
            "Product Name": product_name,
            "Rating": rating_text,
            "Reviews": reviews_count,
            "Current Price": current_price_value,
            "Original Price": strike_through_price_value,
            "Fabric Details": fabric_details.strip(),
            "Fit & Size Details": fit_and_size_details.strip()
        }
    except Exception as e:
        log_message(f"Error while scraping product details: {e}")
        return None

# Function to connect to MySQL database
def connect_to_mysql():
    log_message("Connecting to MySQL database...")
    return mysql.connector.connect(
        host="localhost",
        user="root",  # Replace with your MySQL username
        password="",  # Replace with your MySQL password
        database="scrapefly"  # Replace with your database name
    )

# Function to insert data into MySQL
def store_data_in_mysql(cursor, product_data):
    log_message("Inserting product data into MySQL database...")
    query = """
    INSERT INTO Uniform_Advantage (
        style_number, product_name, rating, reviews, current_price, original_price, fabric_details, fit_and_size_details
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (
        product_data["Style Number"], 
        product_data["Product Name"], 
        product_data["Rating"], 
        product_data["Reviews"], 
        product_data["Current Price"], 
        product_data["Original Price"], 
        product_data["Fabric Details"], 
        product_data["Fit & Size Details"]
    ))
    log_message("Product data inserted successfully.")

# Function to delete all data from the uniform_advantage table
def delete_uniform_advantage_table():
    """Deletes all data from the uniform_advantage table in the MySQL database."""
    try:
        log_message("Connecting to the database to delete existing data...")
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",  # Replace with your MySQL password
            database="scrapefly"  # Replace with your database name
        )
        cursor = connection.cursor()
        sql_query = "DELETE FROM uniform_advantage"
        cursor.execute(sql_query)
        connection.commit()
        log_message("uniform_advantage table data deleted successfully.")

    except mysql.connector.Error as err:
        log_message(f"Error: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            log_message("Database connection closed.")

# Main scraping function
def scrape_uniform_advantage(keyword, num_products):
    log_message(f"Starting scraping process for Uniform Advantage with keyword: {keyword}")
    
    with sync_playwright() as p:
        log_message("Launching browser...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto('https://www.uniformadvantage.com/')

        log_message("Filling in search form...")
        search_box = page.query_selector('#search')
        search_box.fill(keyword)
        search_box.press('Enter')

        log_message(f"Searching for products related to: {keyword}")
        page.wait_for_selector('div.product-grid')

        products = page.query_selector_all('div.product-grid .product')
        log_message(f"Found {len(products)} products.")

        product_data_list = []

        for i, product in enumerate(products[:num_products]):
            log_message(f"Scraping product {i + 1} out of {min(num_products, len(products))}")
            product_link = product.query_selector('a').get_attribute('href')
            page.goto(product_link)
            product_data = scrape_product_details(page)
            if product_data:
                product_data_list.append(product_data)

        log_message(f"Scraped {len(product_data_list)} products. Saving data to database...")

        connection = connect_to_mysql()
        cursor = connection.cursor()
        for product_data in product_data_list:
            store_data_in_mysql(cursor, product_data)
        connection.commit()
        cursor.close()
        connection.close()

        log_message("Scraping completed and data saved to database.")
        browser.close()

        # Convert the list of product data into a pandas DataFrame
        df = pd.DataFrame(product_data_list)

        # Save the DataFrame to an Excel file in the static directory
        output_filename = os.path.join(os.getcwd(), 'static', "scraped_products_uniformadvantage.xlsx")
        df.to_excel(output_filename, index=False)
        log_message(f"Data saved to Excel file: {output_filename}")

        # Clean up the database and close the browser
        delete_uniform_advantage_table()
        log_message("Closing browser...")
        browser.close()
        log_message("Scraping completed successfully.")

# Main entry point
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python uniformadvantage.py <keyword> <num_products>")
        sys.exit(1)

    keyword = sys.argv[1]
    num_products = int(sys.argv[2])
    
    scrape_uniform_advantage(keyword, num_products)
