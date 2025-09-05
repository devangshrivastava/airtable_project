import json
from config import *
from utils.airtable_client import airtable
from utils.helpers import calculate_experience_years, safe_get_field
import datetime
import re

class ApplicantShortlister:
    def __init__(self):
        self.client = airtable
    
    def evaluate_applicant(self, applicant_record):
        """Evaluate single applicant against shortlisting criteria"""
        record_id = applicant_record["id"]
        compressed_json = safe_get_field(applicant_record, "Compressed JSON")
        
        if not compressed_json:
            return {"eligible": False, "reason": "No compressed JSON found"}
        
        try:
            data = json.loads(compressed_json)
        except Exception as e:
            return {"eligible": False, "reason": f"Invalid JSON: {e}"}
        
        # Get linked records for detailed evaluation
        personal_recs = self.client.linked_records(self.client.personal, record_id)
        experience_recs = self.client.linked_records(self.client.experience, record_id)
        salary_recs = self.client.linked_records(self.client.salary, record_id)
        
        # Evaluate criteria
        experience_result = self._evaluate_experience(experience_recs)
        compensation_result = self._evaluate_compensation(salary_recs)
        location_result = self._evaluate_location(personal_recs)
        
        eligible = (
            experience_result["meets_criteria"] and 
            compensation_result["meets_criteria"] and 
            location_result["meets_criteria"]
        )
        
        # reasons that PASSED
        reasons = []
        if experience_result["meets_criteria"]:
            reasons.append(experience_result["reason"])
        if compensation_result["meets_criteria"]:
            reasons.append(compensation_result["reason"])
        if location_result["meets_criteria"]:
            reasons.append(location_result["reason"])

        # reasons that FAILED (for debug printing)
        fail_reasons = []
        if not experience_result["meets_criteria"]:
            fail_reasons.append(f"Experience: {experience_result['reason']}")
        if not compensation_result["meets_criteria"]:
            fail_reasons.append(f"Compensation: {compensation_result['reason']}")
        if not location_result["meets_criteria"]:
            fail_reasons.append(f"Location: {location_result['reason']}")
        
        return {
            "eligible": eligible,
            "reasons": reasons,
            "fail_reasons": fail_reasons,
            "compressed_json": compressed_json,
            "experience": experience_result,
            "compensation": compensation_result,
            "location": location_result
        }
    
    def _evaluate_experience(self, experience_records):
        """Evaluate experience criteria"""
        years = calculate_experience_years(experience_records)
        tier1_company, tier1_name = self._check_tier1_experience(experience_records)
        
        meets_years = years >= MIN_EXPERIENCE_YEARS
        meets_tier1 = tier1_company
        meets_criteria = meets_years or meets_tier1
        
        reasons = []
        if meets_years:
            reasons.append(f"Experience ≥ {MIN_EXPERIENCE_YEARS} years ({years:.1f} yrs)")
        if meets_tier1:
            reasons.append(f"Tier-1 company: {tier1_name}")
        
        return {
            "meets_criteria": meets_criteria,
            "reason": "; ".join(reasons) if reasons else f"Insufficient experience ({years:.1f} yrs)",
            "years": years,
            "tier1_company": tier1_name if tier1_company else None
        }
    
    def _check_tier1_experience(self, experience_records):
        tier1 = {t.lower() for t in TIER1_COMPANIES}
        for rec in experience_records:
            company = safe_get_field(rec, "Company", "").strip().lower()
            if any(t in company for t in tier1):
                return True, safe_get_field(rec, "Company")
        return False, ""
    
    def _evaluate_compensation(self, salary_records):
        """Evaluate compensation criteria"""
        if not salary_records:
            return {"meets_criteria": False, "reason": "No salary information"}
        
        currency = safe_get_field(salary_records[0], "Currency", "").strip().upper()
        preferred_rate = safe_get_field(salary_records[0], "Preferred Rate")
        availability = safe_get_field(salary_records[0], "Availability (hrs/wk)")
        
        try:
            rate_ok = currency == "USD" and float(preferred_rate) <= MAX_HOURLY_RATE
        except (TypeError, ValueError):
            rate_ok = False
        
        try:
            availability_ok = float(availability) >= MIN_AVAILABILITY
        except (TypeError, ValueError):
            availability_ok = False
        
        meets_criteria = rate_ok and availability_ok
        
        if meets_criteria:
            reason = f"Compensation: ≤ ${MAX_HOURLY_RATE}/hr USD and ≥ {MIN_AVAILABILITY} hrs/wk"
        else:
            issues = []
            if not rate_ok:
                issues.append(f"Rate: {preferred_rate} {currency} (needs ≤ ${MAX_HOURLY_RATE} USD)")
            if not availability_ok:
                issues.append(f"Availability: {availability} hrs/wk (needs ≥ {MIN_AVAILABILITY})")
            reason = "; ".join(issues)
        
        return {"meets_criteria": meets_criteria, "reason": reason}
    
    def _evaluate_location(self, personal_records):
        """Evaluate location criteria"""
        if not personal_records:
            return {"meets_criteria": False, "reason": "No location information"}
        
        location = safe_get_field(personal_records[0], "Location", "").strip().lower()
        meets_criteria = any(allowed in location for allowed in ALLOWED_LOCATIONS)
        
        if meets_criteria:
            reason = "Location: Approved region"
        else:
            reason = f"Location: {location} (not in approved regions)"
        
        return {"meets_criteria": meets_criteria, "reason": reason}
    
    def shortlist_applicant(self, applicant_record):
        evaluation = self.evaluate_applicant(applicant_record)

        app_id = applicant_record["id"]
        if evaluation["eligible"]:
            print(f"✅ SELECTED {app_id} -> {', '.join(evaluation['reasons'])}")
        else:
            print(f"❌ REJECTED {app_id} -> {' | '.join(evaluation['fail_reasons'])}")
            return {"shortlisted": False, "reason": "Does not meet criteria"}

        try:
            # ✅ Correct way to set a linked-record field
            shortlist_data = {
                SHORTLIST_LINK_FIELD: [str(applicant_record.get("id"))],  # <-- fix here
                "Compressed JSON": evaluation["compressed_json"],
                "Score Reason": "\n ".join(evaluation["reasons"]),
            }

            # If your airtable client doesn't auto-wrap, uncomment the next line:
            # payload = {"fields": shortlist_data}
            # self.client.shortlisted.create(payload)
            try:
                self.client.shortlisted.create(shortlist_data)

                # Update applicant record status (single-select “yes/no” case)
                self.client.update_applicant(applicant_record["id"], {"Shortlist Status": "yes"})
            except Exception as e:
                print(f"❗ Airtable update failed for {app_id}: {e}")
                # return {"shortlisted": False, "reason": f"Error updating shortlist: {e}"}
            return {"shortlisted": True, "reasons": evaluation["reasons"]}

        except Exception as e:
            print(f"❗ Airtable create failed for {app_id}: {e}")
            return {"shortlisted": False, "reason": f"Error creating shortlist: {e}"}

    def shortlist_all_applicants(self):
        """Evaluate and shortlist all eligible applicants"""
        applicants = self.client.get_all_applicants()
        results = {"success": [], "failed": [], "ineligible": []}
        
        for applicant in applicants:
            record_id = applicant["id"]
            
            # Skip if already shortlisted
            if safe_get_field(applicant, "Shortlist Status") == "yes":
                continue
            
            print(f"⭐ Evaluating applicant {record_id}")
            result = self.shortlist_applicant(applicant)
            
            if result["shortlisted"]:
                results["success"].append((record_id, result["reasons"]))
            elif "Error" in result["reason"]:
                results["failed"].append((record_id, result["reason"]))
            else:
                results["ineligible"].append((record_id, result["reason"]))
        
        return results
