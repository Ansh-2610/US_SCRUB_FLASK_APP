##################################################################

from playwright.sync_api import sync_playwright
import pandas as pd
import sys
import os
import mysql.connector
from datetime import datetime

# Function to log messages with timestamp
def log_message(message):
    """Inserts log messages with a timestamp into the Scrub_harvard_log table."""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="scrapefly"
        )
        cursor = connection.cursor()
        sql_query = "INSERT INTO Scrub_harvard_log (log_message, log_timestamp) VALUES (%s, %s)"
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

# Function to extract product details from a product page
def scrape_product_details(product_page):
    log_message("Extracting product details from product page...")

    # Extract product name
    product_name_element = product_page.query_selector('h1.product-single__title')
    product_name = product_name_element.inner_text().strip() if product_name_element else 'N/A'
    log_message(f"Product name extracted: {product_name}")

    # Extract product price
    price_element = product_page.query_selector('span.product-single__price')
    product_price = price_element.inner_text().strip() if price_element else 'N/A'
    log_message(f"Product price extracted: {product_price}")

    # Extract discount details
    discount_element = product_page.query_selector('p.product__text')
    discount_text = discount_element.inner_text().strip() if discount_element else 'No Discount'
    log_message(f"Product discount extracted: {discount_text}")

    # Extract available colors
    color_elements = product_page.query_selector_all('fieldset[name="color"] input[type="radio"]')
    colors = [color.get_attribute('value') for color in color_elements if color.get_attribute('value')]
    log_message(f"Available colors extracted: {', '.join(colors)}")

    # Extract available sizes
    size_elements = product_page.query_selector_all('fieldset[name="size"] input[type="radio"]')
    sizes = [size.get_attribute('value') for size in size_elements if size.get_attribute('value')]
    log_message(f"Available sizes extracted: {', '.join(sizes)}")

    # Check for free shipping
    free_shipping_element = product_page.query_selector('div.iwt-item__text')
    free_shipping_text = free_shipping_element.inner_text().strip() if free_shipping_element else 'Not Available'
    free_shipping_available = 'Free shipping' in free_shipping_text
    log_message(f"Free shipping available: {free_shipping_available}")

    # Extract product features
    features_element = product_page.query_selector('#gtabb69a53cf-5bc1-4b18-add3-92af436f966c ul')
    features = features_element.query_selector_all('li') if features_element else []
    features_list = [feature.inner_text().strip() for feature in features]
    log_message(f"Product features extracted: {', '.join(features_list)}")

    # Extract care details
    care_element = product_page.query_selector('#gtabf4c1b859-6506-4354-b686-25d6efffda01')
    care_details = care_element.inner_text().strip() if care_element else 'N/A'
    log_message(f"Care instructions extracted: {care_details}")

    return {
        'product_name': product_name,
        'price': product_price,
        'discount': discount_text,
        'available_colors': ', '.join(colors),
        'available_sizes': ', '.join(sizes),
        'free_shipping_available': free_shipping_available,
        'features': ', '.join(features_list),
        'care_details': care_details
    }

# Function to insert the scraped data into the MySQL database
def insert_into_db(data):
    """Insert the scraped data into the MySQL database."""
    try:
        log_message("Connecting to the database...")
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="scrapefly"
        )
        cursor = connection.cursor()
        sql_query = """
            INSERT INTO Scrub_harvard (product_name, price, discount, available_colors, available_sizes, free_shipping_available, features, care_details)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        log_message("Inserting data into the database...")
        cursor.execute(sql_query, (
            data['product_name'], 
            data['price'], 
            data['discount'], 
            data['available_colors'], 
            data['available_sizes'], 
            data['free_shipping_available'], 
            data['features'], 
            data['care_details']
        ))
        connection.commit()
        log_message("Data inserted successfully.")

    except mysql.connector.Error as err:
        log_message(f"Error during database insertion: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            log_message("Database connection closed.")

# Function to delete all data from the Scrub_harvard table
def delete_scrub_harvard_table():
    """Deletes all data from the Scrub_harvard table in the MySQL database."""
    try:
        log_message("Connecting to the database to delete existing data...")
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="scrapefly"
        )
        cursor = connection.cursor()
        sql_query = "DELETE FROM Scrub_harvard"
        cursor.execute(sql_query)
        connection.commit()
        log_message("Scrub_harvard table data deleted successfully.")

    except mysql.connector.Error as err:
        log_message(f"Error: {err}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            log_message("Database connection closed.")

# Main scraping function
def scrape_scrub_harvard(keyword, num_products):
    with sync_playwright() as p:
        log_message("Launching Playwright and navigating to Scrub Harvard website...")
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto('https://www.scrubharvard.com/')

        log_message("Opening search modal...")
        page.click('#shopify-section-sections--22071753048384__header > header > div > div > div > div > div > div.header-bottom__right.col-bottom__right > div.site-header__search-wrap.sidebar__search > details-modal > div > div.header__icon.header__icon--search.header__icon--summary.focus-inset.modal__toggle > span > span > span')
        page.wait_for_selector('#Search-In-Modal')

        log_message(f"Filling in the search keyword: {keyword}")
        page.fill('#Search-In-Modal', keyword)
        page.press('#Search-In-Modal', 'Enter')
        page.wait_for_selector('li.grid__item.js-col')

        product_links = []
        products = page.query_selector_all('li.grid__item.js-col')

        log_message(f"Found {len(products)} products. Extracting product links...")
        for product in products[:num_products]:
            link_element = product.query_selector('a')
            product_link = link_element.get_attribute('href') if link_element else None
            if product_link:
                product_links.append(product_link)

        all_products = []
        log_message(f"Scraping details for {len(product_links)} products...")
        for product_url in product_links:
            if product_url:
                full_product_url = product_url if product_url.startswith("http") else "https://www.scrubharvard.com" + product_url
                log_message(f"Scraping details for: {full_product_url}")
                
                product_page = browser.new_page()
                product_page.goto(full_product_url)

                product_data = scrape_product_details(product_page)
                if product_data:
                    all_products.append(product_data)
                    insert_into_db(product_data)  # Insert into MySQL

                product_page.close()

        log_message("Saving data to Excel...")
        # Close the browser
        browser.close()
        
        # Convert the list of product data into a pandas DataFrame
        df = pd.DataFrame(all_products)
            
        # Save the DataFrame to an Excel file in the static directory
        output_filename = os.path.join(os.getcwd(), 'static', "scraped_products_scrubharvard.xlsx")
        df.to_excel(output_filename, index=False)
        log_message("Data saved successfully.")

        # Clean up the database and close the browser
        delete_scrub_harvard_table()
        log_message("Closing browser...")
        browser.close()
        log_message("Scraping completed successfully.")
        
# Main entry point
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scrubharvard.py <keyword> <num_products>")
        sys.exit(1)

    keyword = sys.argv[1]
    num_products = int(sys.argv[2])
    
    output_file_path = scrape_scrub_harvard(keyword, num_products)
