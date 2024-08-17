from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from django.http import HttpResponse
import logging
import pymongo
from smtplib import SMTP
from email.mime.text import MIMEText

# Configure logging
logger = logging.getLogger(__name__)

def scrape_images(request):
    url = "https://sxc.edu.np/notice"

    # Setup Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Path to your ChromeDriver
    chrome_driver_path = 'E:/chromedriver-win64/chromedriver-win64/chromedriver.exe'
    service = Service(chrome_driver_path)

    # Connect to MongoDB
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client['mis']
    collection = db['notices']

    # Check if the emails collection exists, if not, create it
    if 'emails' not in db.list_collection_names():
        email_collection = db.create_collection('emails')
        # Optionally, you can insert a default email to the new collection
        email_collection.insert_one({"email": "default@example.com"})
    else:
        email_collection = db['emails']

    # List to store messages
    messages = []

    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        # Wait for the JavaScript to load and render the images
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.fixed-image.cover.fixed-image-holder'))
        )

        # Extract image URLs
        img_links = []
        divs = driver.find_elements(By.CSS_SELECTOR, '.fixed-image.cover.fixed-image-holder')
        for div in divs:
            img_tag = div.find_element(By.TAG_NAME, 'img')
            img_link = img_tag.get_attribute('src')
            img_key = img_link.split('/')[-1]
            notice_title = div.find_element(By.XPATH, '..').get_attribute('href').split('/')[-1]

            # Check if the notice already exists in MongoDB
            if not collection.find_one({"_id": notice_title}):
                # Save to MongoDB
                collection.insert_one({
                    "_id": notice_title,
                    "filename": img_key,
                    "img_link": img_link
                })
                logger.debug(f"New notice saved: {notice_title} -> {img_link}")

                # Send email notification
                # send_email_notification(notice_title, img_link, email_collection)
                
                # Append message
                messages.append(f"""
                    <div style="
                        color: black;
                        text-align: center;
                        height: 100vh;
                        margin: 0;
                        padding: 0;
                        font-family: Sans-serif;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                    ">
                        <h1 style="margin-bottom:10px;">New Notice found!!!</h1>
                        <p style="color: green;>Email sent</p>
                        <img src="{img_link}" alt="{img_key}" style="
                            width: auto;
                            height: 70%;
                            object-fit: cover;
                            border-radius: 25px;
                            box-shadow: 0 4px 8px 0 rgba(0, 0, 0, 0.2), 0 6px 20px 0 rgba(0, 0, 0, 0.19);
                        "/>
                    </div>
                """)


        driver.quit()

        # Check if messages list is populated
        if not messages:
            messages.append("<p>No new notices to process.</p>")

        # Return the messages as the HTTP response
        return HttpResponse("<br>".join(messages))

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        if 'driver' in locals():
            driver.quit()
        return HttpResponse("Failed to retrieve content.", status=500)

def send_email_notification(notice_title, img_link, email_collection):
    # Prepare email
    subject = f"New Notice: {notice_title}"
    body = f"A new notice has been detected: {img_link}"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = 'your_email@example.com'

    # Get recipient emails from MongoDB
    recipients = [doc['email'] for doc in email_collection.find()]

    # Send email
    with SMTP('smtp.example.com', 587) as smtp:
        smtp.starttls()
        smtp.login('your_email@example.com', 'your_password')
        for recipient in recipients:
            msg['To'] = recipient
            smtp.send_message(msg)
            logger.debug(f"Email sent to: {recipient}")
