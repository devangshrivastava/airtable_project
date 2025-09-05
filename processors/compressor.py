import json
from utils.airtable_client import airtable
from utils.helpers import safe_get_field, retry_with_backoff
import datetime

class DataCompressor:
    def __init__(self):
        self.client = airtable
    
    def compress_applicant_data(self, applicant_record_id):
        """Compress data from child tables into JSON"""
        try:
            # Get linked records
            personal_records = self.client.linked_records(self.client.personal, applicant_record_id)
            experience_records = self.client.linked_records(self.client.experience, applicant_record_id)
            salary_records = self.client.linked_records(self.client.salary, applicant_record_id)
            
            # Build JSON structure
            json_data = self._build_json_structure(
                personal_records, experience_records, salary_records
            )
            
            # Update applicant record with compressed JSON
            compressed_json = json.dumps(json_data, ensure_ascii=False)
            self.client.update_applicant(applicant_record_id, {
                "Compressed JSON": compressed_json,
            })
            
            return {"success": True, "json_data": json_data}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _build_json_structure(self, personal_recs, exp_recs, salary_recs):
        """Build the compressed JSON structure"""
        # Personal details
        personal_obj = {}
        if personal_recs:
            p = personal_recs[0].get("fields", {})
            if p.get("Full Name"):
                personal_obj["name"] = p["Full Name"]
            if p.get("Email"):
                personal_obj["email"] = p["Email"]
            if p.get("Location"):
                personal_obj["location"] = p["Location"]
            if p.get("LinkedIn"):
                personal_obj["linkedin"] = p["LinkedIn"]
        
        # Experience
        experience_list = []
        for record in exp_recs:
            fields = record.get("fields", {})
            exp_item = {}
            if fields.get("Company"):
                exp_item["company"] = fields["Company"]
            if fields.get("Title"):
                exp_item["title"] = fields["Title"]
            if fields.get("Start"):
                exp_item["start"] = fields["Start"]
            if fields.get("End"):
                exp_item["end"] = fields["End"]
            if fields.get("Technologies"):
                exp_item["technologies"] = fields["Technologies"]
            
            if exp_item:
                experience_list.append(exp_item)
        
        # Salary preferences
        salary_obj = {}
        if salary_recs:
            s = salary_recs[0].get("fields", {})
            if s.get("Preferred Rate") is not None:
                salary_obj["preferred_rate"] = s["Preferred Rate"]
            if s.get("Minimum Rate") is not None:
                salary_obj["minimum_rate"] = s["Minimum Rate"]
            if s.get("Currency"):
                salary_obj["currency"] = s["Currency"]
            if s.get("Availability (hrs/wk)") is not None:
                salary_obj["availability"] = s["Availability (hrs/wk)"]
        
        return {
            "personal": personal_obj,
            "experience": experience_list,
            "salary": salary_obj
        }
    
    @retry_with_backoff()
    def compress_all_applicants(self):
        """Compress all applicants that need compression"""
        applicants = self.client.get_all_applicants()
        results = {"success": [], "failed": [], "skipped": []}
        
        for applicant in applicants:
            record_id = applicant["id"]
            existing_json = safe_get_field(applicant, "Compressed JSON")
            
            # Skip if already compressed (unless forced)
            if existing_json:
                results["skipped"].append(record_id)
                continue
            
            print(f"  📦 Compressing applicant {record_id}")
            result = self.compress_applicant_data(record_id)
            
            if result["success"]:
                results["success"].append(record_id)
            else:
                results["failed"].append((record_id, result["error"]))
                print(f"  ❌ Failed to compress {record_id}: {result['error']}")
        
        return results