## **README**

### **Overview**
This project is a freelance job finder bot built with Python and Aiogram. It automatically scrapes selected freelance websites (sources) and filters results based on a specified minimum price and user-defined skills.

> **Note:** Each freelance marketplace might require adjustments to selectors, prompts, and parsing logic to accommodate differences in their layout.

### **Features**
✅ Automatically scrapes freelance jobs  
✅ Filters jobs by price and required skills  
✅ Sends job notifications via Telegram  
✅ Supports multiple freelance platforms  

### **Requirements**
- Python 3.8 or higher  
- pip (Python package manager)  

### **Installation**
1. Clone the repository to your local machine:
   ```bash
   git clone https://github.com/your-repo/freelance-bot-ai.git
   cd freelance-bot-ai
   ```  
2. From the project root, install dependencies using:  
   ```
   pip install -r requirements.txt
   ```
3. Or run with Docker:
   ```bash
   docker build -t freelance-bot-ai .
   docker run -d --env-file .env freelance-bot-ai
   ```  
   
### **Configuration**
1. Open \`main.py\`.
2. Set your Telegram Bot token in the \`TELEGRAM_TOKEN\` variable.
3. Provide any model API key if required, like in the \`MODEL_API_KEY\` variable.
4. Update the browser path \`BROWSER_PATH\` to your local or preferred browser executable.
5. In the \`ALLOWED_USERS\`, add the Telegram user IDs allowed to access the bot.
6. Modify or add freelance job sources in the \`FREELANCE_SOURCES\` dictionary, specifying CSS selectors as needed.

### **Usage**
1. Run the script:  
   ```
   python main.py
   ```
2. Use Telegram to interact with the bot:
   - **/start** to initialize.  
   - **/skills** to set key skills (e\.g\. `/skills Python, Django`).  
   - **/price** to set minimum price (e\.g\. `/price 100`).  
   - **/interval** to set the interval for notifications (e\.g\. `/interval 30`).  
   - **/start_search** to scrape and filter jobs.  
   - **/stop_search** to end the current search session.

### **Example Interaction**
```
      User: /start
      Bot: 🤖 Welcome! Set your skills and price filter to begin.
      User: /skills Python, Django
      Bot: ✅ Skills updated: Python, Django
      User: /price 100
      Bot: ✅ Minimum price set: $100
      User: /start_search
      Bot: 🔍 Searching for jobs...
```

### **Customization**
- For each freelance aggregator, you may need to adjust CSS selectors (\`selector\`, \`title_selector\`, etc\.) in the source config.
- You can modify or extend the AI prompts in the \`relevance_template\` or \`skills_template\` for better relevance analysis.

### **Disclaimer**
This project is an example. Adjust the code, prompts, scraping methods, and any additional configuration to meet your specific needs.

## 📂 Project Structure  
```bash
├── 📄 main.py              # Main script for the autoresponder
├── 📄 requirements.txt     # Dependencies
├── 📄 .gitignore           # Ignored files list
├── 📄 bot.log    # Log file (auto-generated)
├── 📄 LICENSE              # License file
├── 📄 README.md            # This file
```

## Contact
- **Name:** Stanislav Garipov
- [GitHub Profile](https://github.com/StanGar30)

## License
This project is licensed under the [MIT License](LICENSE).