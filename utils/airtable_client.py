from pyairtable import Api
from config import *

class AirtableClient:
    def __init__(self):
        self.api = Api(AIRTABLE_TOKEN)
        self.applicants = self.api.table(BASE_ID, T_APPLICANTS)
        self.personal = self.api.table(BASE_ID, T_PERSONAL)
        self.experience = self.api.table(BASE_ID, T_EXPERIENCE)
        self.salary = self.api.table(BASE_ID, T_SALARY)
        self.shortlisted = self.api.table(BASE_ID, T_SHORTLISTED)
    
    def get_all_applicants(self):
        """Get all applicants"""
        return self.applicants.all()
    
    def get_applicant(self, record_id):
        """Get single applicant by record ID"""
        return self.applicants.get(record_id)
    
    def update_applicant(self, record_id, fields):
        """Update applicant record"""
        return self.applicants.update(record_id, fields)
    
    def linked_records(self, table, applicant_rec_id):
        """Get records linked to specific applicant"""
        recs = table.all()
        return [r for r in recs if applicant_rec_id in r.get("fields", {}).get(LINK_FIELD, [])]

# Global client instance
airtable = AirtableClient()