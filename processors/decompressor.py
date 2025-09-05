# ============================================================================
import json
from utils.airtable_client import airtable
from utils.helpers import safe_get_field
from config import LINK_FIELD

class DataDecompressor:
    def __init__(self):
        self.client = airtable
    
    def decompress_applicant_data(self, applicant_record_id):
        """Decompress JSON back into child tables"""
        try:
            applicant = self.client.get_applicant(applicant_record_id)
            compressed_json = safe_get_field(applicant, "Compressed JSON")
            
            if not compressed_json:
                return {"success": False, "error": "No compressed JSON found"}
            
            json_data = json.loads(compressed_json)
            
            # Clear existing child records
            self._clear_existing_records(applicant_record_id)
            
            # Recreate from JSON
            self._create_personal_record(applicant_record_id, json_data.get("personal", {}))
            self._create_experience_records(applicant_record_id, json_data.get("experience", []))
            self._create_salary_record(applicant_record_id, json_data.get("salary", {}))
            
            return {"success": True, "json_data": json_data}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _clear_existing_records(self, applicant_record_id):
        """Delete existing child records"""
        for table in [self.client.personal, self.client.experience, self.client.salary]:
            existing_records = self.client.linked_records(table, applicant_record_id)
            for record in existing_records:
                table.delete(record["id"])
    
    def _create_personal_record(self, applicant_record_id, personal_data):
        """Create personal details record"""
        if not personal_data:
            return
        
        fields = {LINK_FIELD: [applicant_record_id]}
        
        if personal_data.get("name"):
            fields["Full Name"] = personal_data["name"]
        if personal_data.get("email"):
            fields["Email"] = personal_data["email"]
        if personal_data.get("location"):
            fields["Location"] = personal_data["location"]
        if personal_data.get("linkedin"):
            fields["LinkedIn"] = personal_data["linkedin"]
        
        if len(fields) > 1:  # More than just the link field
            self.client.personal.create(fields)
    
    def _create_experience_records(self, applicant_record_id, experience_list):
        """Create work experience records"""
        for exp in experience_list:
            fields = {LINK_FIELD: [applicant_record_id]}
            
            if exp.get("company"):
                fields["Company"] = exp["company"]
            if exp.get("title"):
                fields["Title"] = exp["title"]
            if exp.get("start"):
                fields["Start"] = exp["start"]
            if exp.get("end"):
                fields["End"] = exp["end"]
            if exp.get("technologies"):
                fields["Technologies"] = exp["technologies"]
            
            if len(fields) > 1:  # More than just the link field
                self.client.experience.create(fields)
    
    def _create_salary_record(self, applicant_record_id, salary_data):
        """Create salary preferences record"""
        if not salary_data:
            return
        
        fields = {LINK_FIELD: [applicant_record_id]}
        
        if salary_data.get("preferred_rate") is not None:
            fields["Preferred Rate"] = salary_data["preferred_rate"]
        if salary_data.get("minimum_rate") is not None:
            fields["Minimum Rate"] = salary_data["minimum_rate"]
        if salary_data.get("currency"):
            fields["Currency"] = salary_data["currency"]
        if salary_data.get("availability") is not None:
            fields["Availability (hrs/wk)"] = salary_data["availability"]
        
        if len(fields) > 1:  # More than just the link field
            self.client.salary.create(fields)
