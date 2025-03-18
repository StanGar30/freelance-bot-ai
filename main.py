import asyncio
import logging
import re
from typing import List, Dict, Any
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_deepseek import ChatDeepSeek
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.options import Options
import random

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename="bot.log"
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_TOKEN = "TELEGRAM_TOKEN"                            # Your Telegram token
MODEL_API_KEY = "MODEL_API_KEY"                              # Model API key
ALLOWED_USERS = ["ALLOWED_USERS"]                            # List of allowed users (Telegram user IDs)
BROWSER_PATH  = "C:/Program Files/example.exe"  # Path to the browser executable

# Initialize LangChain model or some other model
llm = ChatDeepSeek(
    model="model_name",                         # Your model name
    temperature=0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    api_key=MODEL_API_KEY
)

# List of freelance sources
FREELANCE_SOURCES = {
    "Example_name.com": {
        "name": "Example_name.com",
        "url": "https://www.example_name/projects/",
        "selector": "div.b-post",
        "title_selector": "a.b-post__link",
        "description_selector": "div.b-post__body",
        "price_selector": "div.b-post__price",
        "date_selector": "div.b-post__foot",
    },
}

# User settings
user_settings = {}

# LangChain prompts for relevance analysis and skills extraction(Example prompts)
relevance_template = """
        Please analyze this freelance job and determine how well it matches the following skills: {skills}.
        Give the shortest possible answer, no more than 1 sentence.
        Job:
        Title: {title}
        Description: {description}
        Budget: {price}
        
        Give a relevance score from 0 to 10, where 10 is a perfect match for the skills, and explain your score.
        Return the answer in the format:
        Relevance: [score]
        Reason: [explanation]
        """

# Create a prompt template
relevance_prompt = PromptTemplate(
    input_variables=["skills", "title", "description", "price"],
    template=relevance_template
)

# Skills extraction prompt(Example prompt)
skills_template = """
        The user is looking for freelance jobs with the query: "{query}"
        List 3-5 key skills that may be related to this query.
        Give a very short answer in the form of a list of skills, no more than 1 sentence.
        """

# Create a prompt template
skills_prompt = PromptTemplate(
    input_variables=["query"],
    template=skills_template
)

# LangChain instances for relevance analysis and skills extraction
relevance_chain = LLMChain(llm=llm, prompt=relevance_prompt)
skills_chain = LLMChain(llm=llm, prompt=skills_prompt)

# Dispatcher and bot initialization
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# Handlers for commands
@dp.message(Command("start"))
async def start_handler(message: Message) -> None:
    """Start command handler"""
    user_id = message.from_user.id

    if user_id not in ALLOWED_USERS:
        await message.answer("I'm sorry, you are not allowed to use this bot.")
        return

    # Initialize user settings if not present
    if user_id not in user_settings:
        user_settings[user_id] = {
            "skills": [],                               # User skills
            "sources": list(FREELANCE_SOURCES.keys()),  # Selected sources
            "min_price": 0,                             # Minimum price
            "notification_interval": 30,                # Notification interval in minutes
            "last_jobs": set(),                         # Last found jobs
            "task_running": False                       # Task status
        }

    # Send welcome message(You can customize this message, to example: add a list of available commands)
    await message.answer(
        "Hello! I am a bot for finding freelance jobs. "
        "Use the following commands:\n"
        "/skills - set key skills\n"
        "/sources - select sources for search\n"
        "/price - set minimum price\n"
        "/interval - set notification interval\n"
        "/start_search - start job search\n"
        "/stop_search - stop job search"
    )

# Handlers for setting user skills, sources, minimum price, and notification interval
@dp.message(Command("skills"))
async def set_skills_handler(message: Message) -> None:
    """Skills command handler"""
    user_id = message.from_user.id                                          # Get user ID

    if user_id not in ALLOWED_USERS:                                        # Check if user is allowed
        return

    command_args = message.text.split(maxsplit=1)                           # Split the message text
    if len(command_args) < 2:                                               # Check if the message contains skills
        await message.answer(
            "Create a list of skills separated by commas. For example: /skills Python, Django, Flask, AI"
        )
        return

    skills = [skill.strip() for skill in command_args[1].split(",")]        # Extract skills from the message
    user_settings[user_id]["skills"] = skills                               # Set user skills

    await message.answer(f"Succesfully set skills: {', '.join(skills)}")    # Send a confirmation message

# Handler for setting sources
@dp.message(Command("sources"))
async def set_sources_handler(message: Message) -> None:
    """Sources command handler"""
    user_id = message.from_user.id                                      # Get user ID

    if user_id not in ALLOWED_USERS:                                    # Check if user is allowed
        return

    builder = InlineKeyboardBuilder()
    for source_id, source_info in FREELANCE_SOURCES.items():            # Create a list of sources
        is_selected = source_id in user_settings[user_id]["sources"]    # Check if the source is selected
        status = "✅" if is_selected else "❌"                          # Set the status
        builder.add(InlineKeyboardButton(
            text=f"{source_info['name']} {status}",                     # Add a button for the source
            callback_data=f"source_{source_id}"                         # Set the callback data
        ))

    builder.add(InlineKeyboardButton(
        text="Finish",                                                  # Add a button to finish the selection
        callback_data="sources_done"                                    # Set the callback data
    ))
    builder.adjust(1)                                                   # Adjust the buttons layout

    await message.answer(
        "Choose sources for search:",                              # Send a message to choose sources
        reply_markup=builder.as_markup()                                # Add the keyboard
    )

# Handler for setting the minimum price
@dp.message(Command("price"))
async def set_min_price_handler(message: Message) -> None:
    """/price command handler"""
    user_id = message.from_user.id                                                  # Get user ID

    if user_id not in ALLOWED_USERS:                                                # Check if user is allowed
        return

    command_args = message.text.split(maxsplit=1)                                   # Split the message text
    if len(command_args) < 2 or not command_args[1].isdigit():                      # Check if the message contains the price
        await message.answer("Choose the minimum price. For example: /price 30")    # Send a message to set the price
        return

    min_price = int(command_args[1])                                                # Extract the price from the message
    user_settings[user_id]["min_price"] = min_price                                 # Set the minimum price

    await message.answer(f"Mimimum price set: {min_price}")                         # Send a confirmation message

# Handler for setting the notification interval
@dp.message(Command("interval"))
async def set_interval_handler(message: Message) -> None:
    """/interval command handler"""
    user_id = message.from_user.id                                                          # Get user ID

    if user_id not in ALLOWED_USERS:                                                        # Check if user is allowed
        return

    command_args = message.text.split(maxsplit=1)                                           # Split the message text
    if len(command_args) < 2 or not command_args[1].isdigit():                              # Check if the message contains the interval
        await message.answer("Set the notification interval. For example: /interval 30")    # Send a message to set the interval
        return

    interval = int(command_args[1])                                                         # Extract the interval from the message
    if interval < 5:                                                                        # Check if the interval is at least 5 minutes
        await message.answer("Interval should be at least 5 minutes")
        return

    user_settings[user_id]["notification_interval"] = interval                              # Set the notification interval

    await message.answer(f"Inverval set: {interval} minutes")

# Handler for button clicks
@dp.callback_query()
async def button_callback_handler(callback: types.CallbackQuery) -> None:
    """Button click handler"""
    user_id = callback.from_user.id                                         # Get user ID

    if user_id not in ALLOWED_USERS:                                        # Check if user is allowed
        await callback.answer()                                             # Send a response
        return

    data = callback.data                                                    # Get the callback data

    if data.startswith("source_"):                                          # Check if the data is for a source
        source_id = data.replace("source_", "")                 # Extract the source ID
        if source_id in user_settings[user_id]["sources"]:                  # Check if the source is selected
            user_settings[user_id]["sources"].remove(source_id)             # Remove the source
        else:
            user_settings[user_id]["sources"].append(source_id)             # Add the source

        # Create a keyboard with sources
        builder = InlineKeyboardBuilder()
        for src_id, source_info in FREELANCE_SOURCES.items():               # Create a list of sources
            is_selected = src_id in user_settings[user_id]["sources"]       # Check if the source is selected
            status = "✅" if is_selected else "❌"                          # Set the status
            builder.add(InlineKeyboardButton(
                text=f"{source_info['name']} {status}",                     # Add a button for the source
                callback_data=f"source_{src_id}"                            # Set the callback data
            ))

        builder.add(InlineKeyboardButton(
            text="Finish",                                                  # Add a button to finish the selection
            callback_data="sources_done"                                    # Set the callback data
        ))
        builder.adjust(1)                                                   # Adjust the buttons layout

        await callback.message.edit_text(                                   # Edit the message
            "Select sources for search:",
            reply_markup=builder.as_markup()                                # Add the keyboard
        )

    elif data == "sources_done":                                            # Check if the data is for finishing the selection
        selected_sources = [FREELANCE_SOURCES[s]["name"] for s in user_settings[user_id]["sources"]]    # Get the selected sources
        await callback.message.edit_text(f"Succesfully set sources: {', '.join(selected_sources)}")     # Send a confirmation message
    await callback.answer()                                                                             # Send a response

# Handler for starting the search
@dp.message(Command("start_search"))
async def start_search_handler(message: Message) -> None:
    """/start_search command handler"""
    user_id = message.from_user.id                                                      # Get user ID

    if user_id not in ALLOWED_USERS:                                                    # Check if user is allowed
        return


    # Initialize user settings if not present
    if user_id not in user_settings:
        user_settings[user_id] = {
            "skills": [],                                                               # User skills
            "sources": list(FREELANCE_SOURCES.keys()),                                  # Selected sources
            "min_price": 0,                                                             # Minimum price
            "notification_interval": 30,                                                # Notification interval in minutes
            "last_jobs": set(),                                                         # Last found jobs
            "task_running": False                                                       # Task status
        }

    if not user_settings[user_id]["skills"]:                                            # Check if the user has set skills
        await message.answer("First set the skills using the /skills command")          # Send a message to set the skills
        return

    if user_settings[user_id]["task_running"]:                                          # Check if the search is already running
        await message.answer("Search is already running")                               # Send a message
        return

    user_settings[user_id]["task_running"] = True                                       # Set the task status to running
    user_settings[user_id]["last_jobs"] = set()                                         # Clear the last found jobs

    await message.answer(                                                               # Send a message
        f"Succesfully started search with the following settings:\n"
        f"Searched skills: {', '.join(user_settings[user_id]['skills'])}\n"
        f"Mimimum price: {user_settings[user_id]['min_price']}\n"
        f"Inverval: {user_settings[user_id]['notification_interval']} minutes"
    )

    # Run the search task
    all_jobs = await scrape_all_sources(user_id)                                        # Scrape all sources
    await analyze_jobs_with_ai(all_jobs, user_settings[user_id]["skills"], message)     # Analyze jobs with AI

# Handler for stopping the search
@dp.message(Command("stop_search"))
async def stop_search_handler(message: Message) -> None:
    """/stop_search command handler"""
    user_id = message.from_user.id                      # Get user ID

    if user_id not in ALLOWED_USERS:                    # Check if user is allowed
        return

    if not user_settings[user_id]["task_running"]:      # Check if the search is running
        await message.answer("Search is not running")   # Send a message
        return

    user_settings[user_id]["task_running"] = False      # Set the task status to not running
    await message.answer("Search stopped")              # Send a message

# Asynchronous functions for scraping freelance sources
async def scrape_source(source_info: Dict[str, str], min_price: int) -> List[Dict[str, Any]]:
    """Parse jobs from a single source"""

    # Settings for Selenium
    options = Options()                                                         # Create options
    options.binary_location = BROWSER_PATH                                      # Set the browser path
    options.add_argument("--headless")                                          # Set the headless mode
    options.add_argument("--no-sandbox")                                        # Set the no-sandbox mode
    options.add_argument("--disable-dev-shm-usage")                             # Set the disable-dev-shm-usage mode
    options.add_argument("--disable-gpu")                                       # Set the disable-gpu mode
    options.add_argument("--window-size=1920,1080")                             # Set the window size
    options.add_argument(                                                       # Set the user agent
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")

    timeout_random = random.randint(5, 60)                                  # Set the timeout

    jobs = []
    driver = None
    try:
        # Driver initialization
        driver = webdriver.Chrome(options=options)

        # Iterate over pages
        for page in range(1, 3):
            # URL for the current page
            page_url = f"{source_info['url']}?page={page}"
            driver.get(page_url)

            # Wait for the job elements to load on the page
            wait = WebDriverWait(driver, timeout_random)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, source_info["selector"])))

            # Find job elements on the page
            job_elements = driver.find_elements(By.CSS_SELECTOR, source_info["selector"])
            logger.info(f"Found {len(job_elements)} job elements on page {page}")

            for element in job_elements:
                try:
                    # Data extraction
                    try:
                        # Title and URL, if available
                        title_element = element.find_element(By.CSS_SELECTOR, source_info["title_selector"])
                        title = title_element.text
                        url = title_element.get_attribute("href")
                    except NoSuchElementException:
                        title = "No title"
                        url = ""

                    try:
                        # Description, if available
                        description_element = element.find_element(By.CSS_SELECTOR, source_info["description_selector"])
                        description = description_element.text
                    except NoSuchElementException:
                        description = "No description"

                    try:
                        # Price, if available
                        price_element = element.find_element(By.CSS_SELECTOR, source_info["price_selector"])
                        price_text = price_element.text
                    except NoSuchElementException:
                        price_text = "Цена не указана"

                    try:
                        # Date, if available
                        date_element = element.find_element(By.CSS_SELECTOR, source_info["date_selector"])
                        date_text = date_element.text
                    except NoSuchElementException:
                        date_text = "Дата не указана"

                    # If the URL is relative, add the base URL
                    if url and not url.startswith("http"):
                        base_url = "/".join(source_info["url"].split("/")[:3])          # Create the base URL
                        url = base_url + ('' if url.startswith('/') else '/') + url     # Add the base URL

                    # Remove non-numeric characters from the price
                    price_value = 0
                    if price_text != "Цена не указана":
                        price_matches = re.findall(r'\d+', price_text)
                        if price_matches:
                            price_value = int("".join(price_matches))

                    # Pass the job if the price is less than the minimum
                    if price_value < min_price:
                        continue

                    # Create a job dictionary(You can customize this dictionary)
                    job = {
                        "source": source_info["name"],
                        "title": title,
                        "description": description,
                        "price": price_text,
                        "date": date_text,
                        "url": url,
                        "price_value": price_value,
                        "page": page
                    }

                    jobs.append(job)
                except Exception as e:
                    logger.error(f"Error parsing job element: {e}")
            # Wait for a random time
            await asyncio.sleep(random.randint(3, 7))
    except Exception as e:
        logger.error(f"Error in Selenium scraping for {source_info['name']}: {e}")
    finally:
        # Close the driver
        if driver:
            driver.quit()

    return jobs

# Asynchronous functions for scraping all freelance sources and analyzing jobs with AI
async def scrape_all_sources(user_id: int) -> List[Dict[str, Any]]:
    """Parse jobs from all sources"""
    all_jobs = []

    for source_id in user_settings[user_id]["sources"]:                                                 # Iterate over sources
        source_info = FREELANCE_SOURCES[source_id]                                                      # Get the source info
        try:
            # Run the scraping task
            jobs = await asyncio.to_thread(
                lambda: asyncio.run(scrape_source(source_info, user_settings[user_id]["min_price"]))
            )
            all_jobs.extend(jobs)                                                                       # Add the jobs to the list
        except Exception as e:
            logger.error(f"Error scraping {source_info['name']}: {e}")

    return all_jobs

# Asynchronous function for analyzing jobs with AI
async def analyze_jobs_with_ai(jobs: List[Dict[str, Any]], skills: List[str], message: Message) -> None:
    """Analyze jobs with AI"""
    relevant_jobs = []

    for job in jobs:
        try:
            # Langchain AI analysis
            response = await asyncio.to_thread(
                relevance_chain.run,
                skills=", ".join(skills),                                                   # Set the skills
                title=job["title"],                                                         # Set the title
                description=job["description"],                                             # Set the description
                price=job["price"]                                                          # Set the price
            )

            # Analyze the response
            relevance_score = 0
            relevance_reason = "No reason"

            for line in response.split("\n"):                                               # Iterate over the response lines
                if line.startswith("Relevance:"):                                           # Check if the line contains the relevance score
                    try:
                        relevance_score = int(re.search(r'\d+', line).group())      # Extract the relevance score
                    except:
                        logger.error(f"Error extracting relevance score: {line}")
                elif line.startswith("Reason:"):                                            # Check if the line contains the relevance reason
                    relevance_reason = line.replace("Reason:", "").strip()                  # Extract the relevance reason

            # If the relevance score is high, add the job to the relevant jobs list
            if relevance_score >= 7:
                job["relevance_score"] = relevance_score                                    # Set the relevance score
                job["relevance_reason"] = relevance_reason                                  # Set the relevance reason
                await message.answer(
                    f"Relevant job found:\n{job['title']}\n{job['description']}\nPrice: {job['price']}\nURL: {job['url']}"
                )
            print(f"Relevant jobs count: {len(relevant_jobs)}")
        except Exception as e:
            logger.error(f"Error analyzing job with AI: {e}")
        await asyncio.sleep(20)


# Handler for text messages
@dp.message()
async def process_message(message: Message) -> None:
    """Text message handler"""
    user_id = message.from_user.id                                              # Get user ID

    if user_id not in ALLOWED_USERS:                                            # Check if user is allowed
        return

    text = message.text                                                         # Get the message text

    # Check if the message is a search query
    if re.match(r'^поиск\s+.+', text, re.IGNORECASE):
        query = text.split(None, 1)[1]                              # Extract the search query

        await message.answer(f"Searched query: {query}")                        # Send a message with the search query

        # Imitate a delay
        await asyncio.sleep(2)

        # Use LangChain to extract skills
        try:
            skills = await asyncio.to_thread(
                skills_chain.run,                                               # Run the skills extraction chain
                query=query                                                     # Set the query
            )

            await message.answer(
                f"Suggested skills: {', '.join(skills)}\n"
                f"Use the /skills command to set the skills"
            )
        except Exception as e:
            logger.error(f"Error getting skills from AI: {e}")
            await message.answer("Sorry, I couldn't extract skills from the query")

# Asynchronous function for the main bot loop
async def main() -> None:
    """Run the bot"""
    # Asynchronous bot start
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        # Run the main function
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")