from django.shortcuts import render, redirect
from .models import Email
from .forms import EmailForm
import logging
import pymongo
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logger = logging.getLogger(__name__)

def home(request):
    form = EmailForm()
    if request.method == 'POST':
        form = EmailForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('home')
    
    return render(request, 'home.html', {'form': form})

def send_email(subject, body, recipients, image_links):
    sender_email = "020bim014@sxc.edu.np"
    sender_password = "xaveriangaurav"

    for recipient in recipients:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'plain'))

        # Append image links to the email body
        body += "\n\nImages:\n" + "\n".join(image_links)
        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.set_debuglevel(1)
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, recipient, text)
            server.quit()
            logger.debug(f"Email sent to: {recipient}")
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")

def scrape_images(request):
    try:
        logger.info("Starting the scraping process...")
        
        url = "https://sxc.edu.np/notice"
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_driver_path = 'E:/chromedriver-win64/chromedriver-win64/chromedriver.exe'
        service = Service(chrome_driver_path)

        logger.debug("Initializing MongoDB connection...")
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        db = client['mis']
        collection = db['notices']

        logger.debug("Fetching emails from the database...")
        email_collection = Email.objects.all()
        emails = [email.email for email in email_collection]

        if not emails:
            logger.warning("No emails found in the database.")
        
        messages = []
        image_links = []

        logger.debug("Starting the Chrome WebDriver...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)

        logger.debug("Waiting for notices to load...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.fixed-image.cover.fixed-image-holder'))
        )

        divs = driver.find_elements(By.CSS_SELECTOR, '.fixed-image.cover.fixed-image-holder')
        new_notice_found = False

        for div in divs:
            img_tag = div.find_element(By.TAG_NAME, 'img')
            img_link = img_tag.get_attribute('src')
            img_key = img_link.split('/')[-1]
            notice_title = div.find_element(By.XPATH, '..').get_attribute('href').split('/')[-1]

            if not collection.find_one({"_id": notice_title}):
                logger.debug(f"New notice found: {notice_title}. Saving to database...")
                collection.insert_one({
                    "_id": notice_title,
                    "filename": img_key,
                    "img_link": img_link
                })

                new_notice_found = True
                subject = f"New Notice: {notice_title}"
                body = f"A new notice has been detected: {img_link}"
                image_links.append(img_link)  # Collect image links
                # send_email(subject, body, emails, image_links)

                messages.append(f"Notice: {notice_title}, Email sent to: {', '.join(emails)}")

        driver.quit()

        if not new_notice_found:
            logger.info("No new notices found.")
            return render(request, 'no_new_notice.html')

        logger.info("Scraping completed successfully.")
        return render(request, 'success.html', {'messages': messages, 'images': image_links})

    except Exception as e:
        logger.error(f"Error during scraping: {e}", exc_info=True)
        return render(request, 'error.html')
