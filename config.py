import os
from dotenv import load_dotenv

load_dotenv()

# Airtable Configuration
AIRTABLE_TOKEN = os.environ["AIRTABLE_TOKEN"]
BASE_ID = os.environ["AIRTABLE_BASE_ID"]

# Table Names
T_APPLICANTS = os.environ.get("APPLICANTS_TABLE", "Applicants")
T_PERSONAL = os.environ.get("PERSONAL_TABLE", "Personal Details")
T_EXPERIENCE = os.environ.get("EXPERIENCE_TABLE", "Work Experience")
T_SALARY = os.environ.get("SALARY_TABLE", "Salary Preferences")
T_SHORTLISTED = os.environ.get("SHORTLISTED_TABLE", "Shortlisted Leads")

# Field Names
LINK_FIELD = os.environ.get("APPLICANT_LINK_FIELD", "Applicant ID")
SHORTLIST_LINK_FIELD = os.environ.get("SHORTLIST_LINK_FIELD", "Applicant ID")

# LLM Configuration
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
LLM_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_TOKENS = 500
MAX_RETRIES = 3

# Business Rules
TIER1_COMPANIES = {
    "google", "alphabet", "meta", "facebook", "openai", "microsoft", 
    "apple", "amazon", "netflix", "nvidia", "tesla", "stripe"
}

ALLOWED_LOCATIONS = {
    "us", "canada", "germany", "uk", "india", 
}

MAX_HOURLY_RATE = 100.0
MIN_AVAILABILITY = 20.0
MIN_EXPERIENCE_YEARS = 4.0