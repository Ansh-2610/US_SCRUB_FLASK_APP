from playwright.sync_api import sync_playwright
import pandas as pd
import sys
import os
import time

# Function to scrape product details from a product page
def scrape_product_details(page):
    try:
        print("Getting product name...")
        product_name = page.query_selector('h1.Reviews__Title-sc-1ad046a-20').inner_text()
        print(f"Product Name: {product_name.strip()}")
        
        # Scrape rating
        rating = page.query_selector('.Reviews__ReviewStars-sc-1ad046a-50')
        rating_value = rating.get_attribute('aria-label') if rating else "No rating available"

        # Scrape number of reviews
        reviews_count = page.query_selector('.Reviews__ReviewCountTextHeader-sc-1ad046a-10').inner_text() if page.query_selector('.Reviews__ReviewCountTextHeader-sc-1ad046a-10') else "No reviews"

        # Scrape the current price
        current_price = page.query_selector('span.ProductHighlights__Price-sc-soy3od-5').inner_text() if page.query_selector('span.ProductHighlights__Price-sc-soy3od-5') else "Price not available"

        # Scrape available sizes
        size_buttons = page.query_selector_all('button[role="button"]')  # Select all size buttons
        sizes = [size_button.inner_text().strip() for size_button in size_buttons]

        # Scrape fabric details
        fabric_features = []
        fabric_items = page.query_selector_all('.ProductDetailsAccordionSection__FeaturesWrapper-sc-1fnl6ky-6.izBubJ')
        for item in fabric_items:
            fabric_features.append(item.inner_text().strip())
        
        care_instructions = page.query_selector('.ProductDetailsAccordionSection__RawMaterials-sc-1fnl6ky-3.bgHrpi')
        care_instructions_text = care_instructions.inner_text().strip() if care_instructions else "Care instructions not available"

        # Return the scraped product details as a dictionary
        return {
            "Product Name": product_name.strip(),
            "Rating": rating_value.strip(),
            "Reviews": reviews_count.strip(),
            "Current Price": current_price.strip(),
            "Available Sizes": "; ".join(sizes),
            "Details & Fit": "; ".join(fabric_features),
            "Fabric & Care Instructions": care_instructions_text,
        }

    except Exception as e:
        print(f"Error while scraping product details: {e}")
        return None

# Main function to search for products and scrape details
def main(keyword, num_products):
    # List to hold all scraped data
    all_products = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        # Navigate to the search page
        search_url = "https://www.wearfigs.com/"
        page.goto(search_url)

        # Click on the search tab
        page.wait_for_selector('#onetrust-reject-all-handler', timeout=5000)
        page.click('#onetrust-reject-all-handler')
        page.click('#nav-tab-search button')

        # Wait for the search overlay to appear
        page.wait_for_selector('.SearchOverlay__ExpansionPanelWrapper-sc-1nghzfs-0', timeout=10000)

        # Fill in the search input field with the keyword
        page.fill('input[name="searchText"]', keyword)

        # Click the search button to submit
        page.press('input[name="searchText"]', 'Enter')

        # Wait for the initial search results to load
        page.wait_for_selector('.Collection__StyledGridItem-sc-1ustqhb-1.gQZWxk', timeout=10000)

        # List to hold product links
        product_links = []
        
        # Scroll and collect product links until the desired number is reached
        while len(product_links) < num_products:
            # Wait for product tiles to load
            page.wait_for_selector('.Collection__StyledGridItem-sc-1ustqhb-1.gQZWxk', timeout=5000)
            new_links = page.query_selector_all('.Collection__StyledGridItem-sc-1ustqhb-1.gQZWxk a')
            product_links.extend(link.get_attribute('href') for link in new_links)

            # Remove duplicates
            product_links = list(set(product_links))

            # Check if we have enough products
            if len(product_links) >= num_products:
                break

            # Scroll down to load more products
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)  # Adjust the waiting time as per the loading speed of the website

        # Limit the product links to the specified number
        product_links = product_links[:num_products]

        # Loop through the product links and scrape details
        for product_url in product_links:
            if product_url:
                full_product_url = product_url if product_url.startswith("http") else "https://www.wearfigs.com" + product_url
                print(f"Scraping details for: {full_product_url}")
                product_page = browser.new_page()  # Create a new page for each product
                product_page.goto(full_product_url)
                product_data = scrape_product_details(product_page)
                if product_data:
                    all_products.append(product_data)
                product_page.close()  # Close the page after scraping

        # Close the browser
        browser.close()

    # Convert the list of product data into a pandas DataFrame
    df = pd.DataFrame(all_products)

    # Save the DataFrame to an Excel file in the static directory
    output_filename = os.path.join(os.getcwd(), 'static', "scraped_products_wearfigs.xlsx")
    df.to_excel(output_filename, index=False)

    print(f"Scraping complete. Data saved to '{output_filename}'.")

if __name__ == "__main__":
    # Get keyword and number of products from command-line arguments
    if len(sys.argv) != 3:
        print("Usage: python WearFigs.py <keyword> <num_products>")
    else:
        keyword_arg = sys.argv[1]
        num_products_arg = int(sys.argv[2])
        main(keyword_arg, num_products_arg)