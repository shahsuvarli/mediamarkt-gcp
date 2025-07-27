import requests
from bs4 import BeautifulSoup
import json
import time
import sys
import csv
from google.cloud import storage

BASE_URL = "https://www.mediamarkt.de"
BRAND_URL = f"{BASE_URL}/de/brand"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}


GCS_BUCKET = "my-mediamarkt-project"
GCS_FILENAME = "mediamarkt_products.csv"

def get_soup(url):
    resp = requests.get(url, headers=HEADERS)
    time.sleep(0.5)
    return BeautifulSoup(resp.text, "html.parser")

def get_letter_anchors(soup):
    anchors = []
    anchor_div = soup.find("div", {"data-test": "mms-search-glossary-anchors"})
    if anchor_div:
        for a in anchor_div.find_all("a"):
            letter = a.get("aria-label")
            if letter:
                anchors.append(letter)
    return anchors

def get_brands_for_letter(soup, letter):
    brands = []
    section = soup.find("div", {"id": f"glossary-row-{letter}"})
    if section:
        ul = section.find("ul")
        if ul:
            for li in ul.find_all("li"):
                a_tag = li.find("a")
                if a_tag and a_tag.get("href"):
                    brands.append({
                        "brand_name": a_tag.text.strip(),
                        "brand_link": BASE_URL + a_tag["href"]
                    })
    return brands

def is_return_button(cat_name, cat_link, parent_url):
    if not cat_name or not cat_link:
        return True
    lower_name = cat_name.lower()
    if "zurück" in lower_name or "zurueck" in lower_name or "previous" in lower_name or "back" in lower_name:
        return True
    if cat_link.rstrip('/') == parent_url.rstrip('/'):
        return True
    return False

def get_categories_from_page(page_url):
    soup = get_soup(page_url)
    categories = []
    for cat in soup.find_all("div", {"data-test": "brand-category"}):
        cat_name_tag = cat.find("p", {"data-test": "mms-brand-category-tile-link-text"})
        cat_name = cat_name_tag.text.strip() if cat_name_tag else None
        a_tag = cat.find("a")
        cat_link = BASE_URL + a_tag["href"] if a_tag and a_tag.get("href") else None
        img_tag = cat.find("img")
        img_url = img_tag["src"] if img_tag else None
        if is_return_button(cat_name, cat_link, page_url):
            continue
        if cat_name and cat_link:
            categories.append({
                "category_name": cat_name,
                "category_link": cat_link,
                "category_image": img_url,
                "subcategories": [],
                "products": []
            })
    return categories

def get_products_from_category(category_url):
    soup = get_soup(category_url)
    products = []
    for card in soup.find_all("article", {"data-test": "mms-product-card"}):
        title_tag = card.find("p", {"data-test": "product-title"})
        title = title_tag.text.strip() if title_tag else None

        link_tag = card.find("a", {"data-test": "mms-router-link-product-list-item-link_mp"})
        link = BASE_URL + link_tag["href"] if link_tag and link_tag.get("href") else None

        # Previous rating (container text)
        rating_container = card.find("div", {"data-test": "mms-customer-rating-container"})
        rating_text = rating_container.text.strip() if rating_container else None

        # New rating (aria-label)
        rating_aria_label = None
        rating_div = card.find("div", {"data-test": "mms-customer-rating"})
        if rating_div and rating_div.has_attr("aria-label"):
            rating_aria_label = rating_div["aria-label"]

        price_tag = card.find("span", class_="sc-e0c7d9f7-0 bPkjPs")
        price = price_tag.text.strip() if price_tag else None

        # Product image
        image_tag = card.find("picture", {"data-test": "product-image"})
        img_url = None
        if image_tag:
            img = image_tag.find("img")
            if img and img.get("src"):
                img_url = img["src"]

        details = {}
        dl_tag = card.find("dl")
        if dl_tag:
            dt_tags = dl_tag.find_all("dt")
            dd_tags = dl_tag.find_all("dd")
            for dt, dd in zip(dt_tags, dd_tags):
                key_tag = dt.find("p")
                value_tag = dd.find("p")
                key = key_tag.text.strip() if key_tag else None
                value = value_tag.text.strip() if value_tag else None
                if key and value:
                    details[key] = value

        products.append({
            "title": title,
            "link": link,
            "image": img_url,
            "rating_text": rating_text,
            "rating_aria_label": rating_aria_label,
            "price": price,
            "details": json.dumps(details, ensure_ascii=False)
        })
    return products

def scrape_category_recursive(category, parent_url, visited=None):
    if visited is None:
        visited = set()
    if category["category_link"] in visited:
        print(f"Already visited {category['category_link']}, skipping to avoid loop.")
        return
    visited.add(category["category_link"])
    try:
        subcategories = get_categories_from_page(category["category_link"])
        if subcategories:
            for subcat in subcategories:
                scrape_category_recursive(subcat, category["category_link"], visited)
            category["subcategories"] = subcategories
        else:
            products = get_products_from_category(category["category_link"])
            category["products"] = products
    except Exception as e:
        print(f"Error scraping category {category.get('category_name', '')}: {e}")

def flatten_for_csv(data):
    rows = []
    for brand in data:
        brand_name = brand.get("brand_name", "")
        for category in brand.get("categories", []):
            cat_name = category.get("category_name", "")
            cat_link = category.get("category_link", "")
            cat_img = category.get("category_image", "")
            if category.get("subcategories"):
                for subcat in category["subcategories"]:
                    subcat_name = subcat.get("category_name", "")
                    subcat_link = subcat.get("category_link", "")
                    subcat_img = subcat.get("category_image", "")
                    for product in subcat.get("products", []):
                        rows.append([
                            brand_name, cat_name, cat_link, cat_img,
                            subcat_name, subcat_link, subcat_img,
                            product.get("title", ""), product.get("link", ""),
                            product.get("image", ""), product.get("rating_text", ""), product.get("rating_aria_label", ""),
                            product.get("price", ""), product.get("details", "")
                        ])
            else:
                for product in category.get("products", []):
                    rows.append([
                        brand_name, cat_name, cat_link, cat_img,
                        "", "", "",
                        product.get("title", ""), product.get("link", ""),
                        product.get("image", ""), product.get("rating_text", ""), product.get("rating_aria_label", ""),
                        product.get("price", ""), product.get("details", "")
                    ])
        if brand.get("products"):
            for product in brand["products"]:
                rows.append([
                    brand_name, "", "", "",
                    "", "", "",
                    product.get("title", ""), product.get("link", ""),
                    product.get("image", ""), product.get("rating_text", ""), product.get("rating_aria_label", ""),
                    product.get("price", ""), product.get("details", "")
                ])
    return rows

def save_csv_to_gcs(rows, bucket_name, filename):
    local_file = "/tmp/" + filename
    headers = [
        "brand_name", "category_name", "category_link", "category_image",
        "subcategory_name", "subcategory_link", "subcategory_image",
        "product_title", "product_link", "product_image",
        "product_rating_text", "product_rating_aria_label",
        "product_price", "product_details"
    ]
    with open(local_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    blob.upload_from_filename(local_file)
    print(f"CSV uploaded to gs://{bucket_name}/{filename}")

def main():
    all_data = []
    try:
        soup = get_soup(BRAND_URL)
        letters = get_letter_anchors(soup)
        for letter in letters[:1]:
            print(f"Scraping brands for letter: {letter}")
            brands = get_brands_for_letter(soup, letter)
            for brand in brands:
                print(f"  Scraping brand: {brand['brand_name']}")
                categories = get_categories_from_page(brand["brand_link"])
                if categories:
                    for category in categories:
                        print(f"    Scraping category: {category['category_name']}")
                        scrape_category_recursive(category, brand["brand_link"])
                    brand["categories"] = categories
                else:
                    print(f"    No categories found, scraping products directly for brand: {brand['brand_name']}")
                    brand["categories"] = []
                    brand["products"] = get_products_from_category(brand["brand_link"])
                all_data.append(brand)
        rows = flatten_for_csv(all_data)
        save_csv_to_gcs(rows, GCS_BUCKET, GCS_FILENAME)
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)
    print("Scraping complete. Results uploaded to Google Cloud Storage.")

if __name__ == "__main__":
    main()