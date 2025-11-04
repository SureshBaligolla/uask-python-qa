# QA Automation Case Study — U-Ask Chatbot (GovGPT)

### 👤 Author
**Suresh Baligolla**

---

## 📘 Overview
Automated end-to-end testing framework for the UAE Government’s **U-Ask (GovGPT)** chatbot.

Validates:
- Chatbot UI functionality (load, send, response, clear, scroll)
- AI/ML semantic correctness using OpenAI embeddings
- Multilingual support (English & Arabic)
- Security input sanitization & malicious prompt handling

---

## 🧱 Project Structure
uask-python-qa/
│
├── tests/                       # All test cases
│   └── test_chat_validation.py  # Semantic + security validation
│   └── test_layout_direction.py # LTR/RTL direction tests (optional)
│
├── pages/                       # Page Object Model (POM)
│   ├── login_page.py            # Login functionality
│   └── chat_page.py             # Chat screen actions and message handling
│
├── utils/                       
│   ├── config.py                # Global constants, URLs, and thresholds
│   └── openai_validator.py      # Embedding-based semantic scoring
│
├── test_data/
│   └── test-data.json           # Prompts and expected responses
│
├── reports/
│   ├── test_report.html         # Pytest HTML output
│   └── allure-results/          # Allure result files
│
├── screenshots/                 # Captured images during test runs
├── conftest.py                  # PyTest driver fixture (setup + teardown)
├── requirements.txt             # Dependencies
└── README.md


1.Install dependencies
pip install -r requirements.txt

2.Set your OpenAI API key
export OPENAI_API_KEY=your_api_key_here

3.Run all tests
pytest -v --alluredir=reports/allure-results

4.View live Allure report
allure serve reports/allure-results

Delete allure reporst
rm -rf reports/allure-results reports/allure-report

run all : pytest -v --alluredir=reports/allure-results       
allure serve reports/allure-results 


5.Language Configuration

The chatbot supports both English and Arabic test data.

To configure:

Open test_data/test-data.json

Add your prompts and expected responses.

Example:

[
  {
    "prompt_en": "Hello",
    "expected_en": "Hello! How can I assist you today?",
    "prompt_ar": "مرحبا",
    "expected_ar": "مرحبًا! كيف يمكنني مساعدتك اليوم؟"
  }
]

6.Semantic Validation (AI/ML)

Instead of keyword matching, this project uses OpenAI text-embedding-3-small to evaluate response meaning.

Expected and actual responses are embedded as numerical vectors.

Cosine similarity measures how close they are in meaning.

A similarity threshold (default 0.6) determines a pass/fail.

similarity = openai_validator.calculate_similarity(expected, actual)
assert similarity >= config.SIMILARITY_THRESHOLD


Benefits:

Robust to paraphrases and synonyms

Works across multiple languages

Fewer false failures compared to string matching



Maintainer: Suresh Baligolla


Run offline reports

cd reports/allure-report
python3 -m http.server 8000











