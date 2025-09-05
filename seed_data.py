import os, random
from dotenv import load_dotenv
from pyairtable import Api
import datetime

load_dotenv()

AIRTABLE_TOKEN = os.environ["AIRTABLE_TOKEN"]
BASE_ID = os.environ["AIRTABLE_BASE_ID"]

T_APPLICANTS = os.environ.get("APPLICANTS_TABLE", "Applicants")
T_PERSONAL = os.environ.get("PERSONAL_TABLE", "Personal Details")
T_EXPERIENCE = os.environ.get("EXPERIENCE_TABLE", "Work Experience")
T_SALARY = os.environ.get("SALARY_TABLE", "Salary Preferences")
LINK_FIELD = os.environ.get("APPLICANT_LINK_FIELD", "Applicant ID")

api = Api(AIRTABLE_TOKEN)
applicants = api.table(BASE_ID, T_APPLICANTS)
personal = api.table(BASE_ID, T_PERSONAL)
experience = api.table(BASE_ID, T_EXPERIENCE)
salary = api.table(BASE_ID, T_SALARY)

TIER1 = ["Google", "Meta", "OpenAI", "Microsoft", "Apple"]
OTHERS = ["StartupX", "LocalSoft", "EduTech", "RetailCorp", "BankInc"]
LOCATIONS = ["US", "Canada", "Germany", "UK",
             "India", "France", "Australia"]

def clear_all():
    print("Clearing existing records...")
    # delete children first, then parents
    for tbl in [personal, experience, salary, applicants]:
        for r in tbl.all():
            tbl.delete(r["id"])

def seed():
    print("Creating mock applicants...")
    for i in range(1, 12):
        app = applicants.create({"Applicant ID": f"APP{i:03}"})
        app_id = app["id"]

        personal.create({
            LINK_FIELD: [app_id],
            "Full Name": f"Candidate {i}",
            "Email": f"candidate{i}@example.com",
            "Location": random.choice(LOCATIONS),
            "LinkedIn": f"https://linkedin.com/in/candidate{i}"
        })

        for _ in range(random.randint(1, 3)):
            company = random.choice(TIER1 + OTHERS)
            years = random.randint(3, 8)
            today = datetime.date.today()
            end_date = today - datetime.timedelta(days=random.randint(0, 365))  # up to ~1 year ago
            start_date = end_date - datetime.timedelta(days=years * 365)
            title = random.choice(["SWE", "Engineer", "Data Scientist", "Product Dev"])
            experience.create({
                LINK_FIELD: [app_id],
                "Company": company,
                "Title": title,
                "Start": start_date.isoformat(),
                "End": end_date.isoformat(),
                "Technologies": random.choice(["Python", "JS", "C++", "Go"])
            })

        pref_rate = random.choice([50, 60, 65, 70, 75, 80, 90, 100, 120, 150])
        avail = random.choice([15, 20, 25, 30, 35])
        currency = random.choice(["USD"])
        salary.create({
            LINK_FIELD: [app_id],
            "Preferred Rate": pref_rate,
            "Minimum Rate": max(50, pref_rate - 20),
            "Currency": currency,
            "Availability (hrs/wk)": avail
        })
        print(f"  - Created applicant APP{i:03}")
    print("✅ Seed complete: 10 applicants created.")

def main():
    clear_all()
    seed()

if __name__ == "__main__":
    main()
