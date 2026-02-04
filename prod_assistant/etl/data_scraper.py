import csv
import time
import re
import os
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

class FlipkartScraper:
    def __init__(self, output_dir="data"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        if not hasattr(uc.ChromeOptions, "headless"):
            uc.ChromeOptions.headless = False

    def get_top_reviews(self,product_url,count=2):
        """Get the top reviews for a product.
        """
        options = uc.ChromeOptions()
        options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--remote-debugging-port=0")

        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = uc.Chrome(options=options,  use_subprocess=False, headless=False)

        if not product_url.startswith("http"):
            driver.quit()
            return "No reviews found"

        try:
            driver.get(product_url)
            time.sleep(4)
            try:
                driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
                time.sleep(1)
            except Exception as e:
                print(f"Error occurred while closing popup: {e}")

            for _ in range(4):
                ActionChains(driver).send_keys(Keys.END).perform()
                time.sleep(1.5)

            soup = BeautifulSoup(driver.page_source, "html.parser")
            headlines = soup.select("p.qW2QI1, p._2-N8zT, p._2xg6Ul")
            bodies = soup.select("div.G4PxIA, div._6K-7Co, div._27M-vq, div.t-ZTKy, div.col.EPCmJX")

            seen = set()
            reviews = []

            for h, b in zip(headlines, bodies):
                text = f"{h.get_text(strip=True)} — {b.get_text(' ', strip=True)}"
                if text and text not in seen:
                    reviews.append(text)
                    seen.add(text)
                if len(reviews) >= count:
                    break

        except Exception:
            reviews = []

        driver.quit()
        return " || ".join(reviews) if reviews else "No reviews found"
    
    def scrape_flipkart_products(self, query, max_products=1, review_count=2):
        """Scrape Flipkart products based on a search query.
        """
        options = uc.ChromeOptions()
        options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--remote-debugging-port=0")

        options.add_argument("--disable-blink-features=AutomationControlled")
        driver = uc.Chrome(options=options,  use_subprocess=False, headless=False)
        time.sleep(2)

        try:
            search_url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
            driver.get(search_url)
            time.sleep(5)

            try:
                driver.find_element(By.XPATH, "//button[contains(text(), '✕')]").click()
            except Exception as e:
                print(f"Error occurred while closing popup: {e}")

            time.sleep(2)
            products = []

            items = driver.find_elements(By.CSS_SELECTOR, "div[data-id]")[:max_products]
            print("FOUND ITEMS:", len(items))
            # if items:
            #     print(items[0].get_attribute("outerHTML"))


            for item in items:
                def safe_text(el, selector):
                    try:
                        return el.find_element(By.CSS_SELECTOR, selector).text.strip()
                    except Exception:
                        return "N/A"

                title = safe_text(item, "div.RG5Slk")
                price = safe_text(item, "div.hZ3P6w")
                rating = safe_text(item, "div.MKiFS6")
                reviews_text = safe_text(item, "span.PvbNMB")


                match = re.search(r"([\d,]+)\s+Reviews", reviews_text)
                total_reviews = match.group(1) if match else "N/A"


                try:
                    link_el = item.find_element(By.CSS_SELECTOR, "a.k7wcnx")
                    href = link_el.get_attribute("href")
                    product_link = href if href.startswith("http") else "https://www.flipkart.com" + href
                    match = re.findall(r"/p/(itm[0-9A-Za-z]+)", href)
                    product_id = match[0] if match else "N/A"
                except Exception as e:
                    print(f"Error occurred while extracting product link: {e}")
                    continue

                top_reviews = self.get_top_reviews(product_link, count=review_count) if "flipkart.com" in product_link else "Invalid product URL"
                products.append([product_id, title, rating, total_reviews, price, top_reviews])
        finally:
            driver.quit()
        return products
    
    def save_to_csv(self, data, filename="product_reviews.csv"):
        """Save the scraped product reviews to a CSV file."""
        if os.path.isabs(filename):
            path = filename
        elif os.path.dirname(filename):  # filename includes subfolder like 'data/product_reviews.csv'
            path = filename
            os.makedirs(os.path.dirname(path), exist_ok=True)
        else:
            # plain filename like 'output.csv'
            path = os.path.join(self.output_dir, filename)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_id", "product_title", "rating", "total_reviews", "price", "top_reviews"])
            writer.writerows(data)
        
