import json
import time
import hashlib
from groq import Groq
from config import *
from utils.airtable_client import airtable
from utils.helpers import safe_get_field, retry_with_backoff
from config import MAX_TOKENS
import datetime

class LLMEvaluator:
    def __init__(self):
        self.client = airtable
        self.groq_client = Groq(api_key=GROQ_API_KEY)
        self.model = LLM_MODEL
    

    # def _build_evaluation_prompt(self, json_data):
    #     """Build the LLM evaluation prompt"""
    #     return f"""You are a recruiting analyst. Given the following applicant JSON, do four things:

    # 1. Provide a concise 75-word summary of the candidate
    # 2. Rate overall candidate quality from 1–10 (higher is better) 
    # 3. List any data gaps or inconsistencies you notice
    # 4. Suggest up to three follow-up questions to clarify gaps or assess fit

    # Applicant JSON:
    # {json.dumps(json_data, indent=2)}

    # Return your answer strictly as a valid JSON object with this schema:

    # {{
    # "summary": "string (<=75 words)",
    # "score": integer (1–10),
    # "issues": ["list of strings, or empty if none"],
    # "follow_ups": ["list of up to 3 follow-up questions"]
    # }}

    import json

    def _build_evaluation_prompt(self, json_data):
        """Build the LLM evaluation prompt with JSON-structured instructions"""
        prompt = {
            "role": {
                "persona": "You are a recruiting analyst evaluating candidates based on their resumes and job data."
            },
            "instructions": {
                "task": [
                    "Write a concise professional summary (<= 75 words).",
                    "Assign an overall candidate quality score from 1 to 10 (higher = stronger).",
                    "List any missing information, inconsistencies, or ambiguities.",
                    "Suggest up to 3 follow-up questions to clarify gaps or assess fit."
                ],
                "rules": [
                    "Output must be ONLY valid JSON.",
                    "Never leave any field empty or null.",
                    "If nothing applies, use [] for arrays.",
                    "Keep summary professional and <= 75 words.",
                    "Score must be an integer between 1 and 10 (no decimals)."
                ],
                "output_schema": {
                    "summary": "string (<= 75 words)",
                    "score": "integer (1-10)",
                    "issues": ["list of strings or []"],
                    "follow_ups": ["list of up to 3 strings or []"]
                }
            },
            "example": {
                "input": {
                    "personal": {
                        "name": "Candidate 2",
                        "email": "candidate2@example.com",
                        "location": "Berlin, Germany",
                        "linkedin": "https://linkedin.com/in/candidate2"
                    },
                    "experience": [
                        {
                            "company": "StartupX",
                            "title": "Product Dev",
                            "start": "2024-07-28",
                            "end": "2025-07-28",
                            "technologies": "Python"
                        },
                        {
                            "company": "StartupX",
                            "title": "SWE",
                            "start": "2018-09-10",
                            "end": "2024-09-08",
                            "technologies": "Python"
                        }
                    ],
                    "salary": {
                        "preferred_rate": 150,
                        "minimum_rate": 130,
                        "currency": "INR",
                        "availability": 15
                    }
                },
                "output": {
                    "summary": "Candidate 2 is a software engineer with 6+ years at StartupX, working in product development and software engineering roles with strong Python expertise. Based in Berlin, Germany, the candidate demonstrates consistency in long-term engagement and adaptability within startup environments.",
                    "score": 7,
                    "issues": [
                        "No details on specific projects or achievements",
                        "Salary expectation listed in INR despite location in Germany",
                        "Limited tech stack beyond Python"
                    ],
                    "follow_ups": [
                        "Can you provide examples of projects you led or contributed to at StartupX?",
                        "Are you open to salary negotiation in EUR or USD given your current location?",
                        "Do you have experience with other technologies beyond Python?"
                    ]
                }
            },
            "input": json_data
        }
        return json.dumps(prompt, indent=2)


    def _parse_llm_response(self, response_text):
        """Parse structured response from LLM"""
        lines = response_text.strip().split('\n')
        print("LLM raw response lines:", lines)
        print("\n\n")
        result = {
            "summary": "",
            "score": 0,
            "issues": "",
            "follow_ups": ""
        }
        
        current_section = None
        content_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith("Summary:"):
                if current_section:
                    result[current_section] = '\n'.join(content_lines).strip()
                current_section = "summary"
                content_lines = [line[8:].strip()]
            elif line.startswith("Score:"):
                if current_section:
                    result[current_section] = '\n'.join(content_lines).strip()
                current_section = "score"
                try:
                    result["score"] = int(line[6:].strip())
                except ValueError:
                    result["score"] = 0
                content_lines = []
            elif line.startswith("Issues:"):
                if current_section:
                    result[current_section] = '\n'.join(content_lines).strip()
                current_section = "issues"
                content_lines = [line[7:].strip()]
            elif line.startswith("Follow-Ups:"):
                if current_section:
                    result[current_section] = '\n'.join(content_lines).strip()
                current_section = "follow_ups"
                content_lines = [line[11:].strip()]
            elif current_section and line:
                content_lines.append(line)
        
        # Handle last section
        if current_section and content_lines:
            result[current_section] = '\n'.join(content_lines).strip()
        
        return result
    
    def _get_json_hash(self, json_data):
        """Generate hash of JSON data to detect changes"""
        json_str = json.dumps(json_data, sort_keys=True)
        return hashlib.md5(json_str.encode()).hexdigest()
    
    @retry_with_backoff()
    def evaluate_applicant(self, applicant_record):
        """Evaluate single applicant with LLM"""
        record_id = applicant_record["id"]
        compressed_json = safe_get_field(applicant_record, "Compressed JSON")
        
        if not compressed_json:
            return {"success": False, "error": "No compressed JSON found"}
        
        try:
            json_data = json.loads(compressed_json)
        except Exception as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}
        
        # Check if we need to re-evaluate (data changed)
        current_hash = self._get_json_hash(json_data)
        stored_hash = safe_get_field(applicant_record, "LLM Data Hash")
        
        if stored_hash == current_hash and safe_get_field(applicant_record, "LLM Summary"):
            return {"success": True, "skipped": True, "reason": "No changes detected"}
        
        try:
            # Call LLM
            # print("user data",json_data)
            prompt = self._build_evaluation_prompt(json_data)
            
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=MAX_TOKENS,
                temperature=0.3,
                response_format={
                    "type" : "json_object"
                    # "type": "json_schema",
                    # "json_schema": {
                    #     "type": "object",
                    #     "properties": {
                    #         "summary": {"type": "string"},
                    #         "score": {"type": "integer"},
                    #         "issues": {"type": "array", "items": {"type": "string"}},
                    #         "follow_ups": {"type": "array", "items": {"type": "string"}}
                    #     },
                    #     "required": ["summary", "score", "follow_ups"]
                    # }
                }
            )
            
            response_text = response.choices[0].message.content
            stripped_response = response_text.strip()
            try:
                parsed_result = json.loads(stripped_response)
            except json.JSONDecodeError:
                parsed_result = self._parse_llm_response(response_text)

            # print(f"LLM Response for {record_id} \nParsed: {parsed_result}")
            # Update Airtable record
            followups_text = "\n".join(parsed_result["follow_ups"])
            update_fields = {
                "LLM Summary": parsed_result["summary"],
                "LLM Score": parsed_result["score"],
                "LLM Follow-Ups": followups_text,
            }
            
            self.client.update_applicant(record_id, update_fields)
            
            return {
                "success": True,
                "skipped": False,
                "evaluation": parsed_result,
                "tokens_used": response.usage.total_tokens if hasattr(response, 'usage') else 0
            }
            
        except Exception as e:
            return {"success": False, "error": f"LLM evaluation failed: {e}"}
    
    def evaluate_all_applicants(self, force_reprocess=False):
        """Evaluate all applicants with LLM"""
        applicants = self.client.get_all_applicants()
        results = {"success": [], "failed": [], "skipped": []}
        total_tokens = 0
        
        for applicant in applicants:
            record_id = applicant["id"]
            
            # Skip if no compressed JSON
            if not safe_get_field(applicant, "Compressed JSON"):
                results["skipped"].append((record_id, "No compressed JSON"))
                continue
            
            print(f"  🤖 Evaluating applicant {record_id} with LLM")
            result = self.evaluate_applicant(applicant)
            
            if result["success"]:
                if result.get("skipped"):
                    results["skipped"].append((record_id, result["reason"]))
                    print(f"    ⏭️  Skipped: {result['reason']}")
                else:
                    results["success"].append(record_id)
                    total_tokens += result.get("tokens_used", 0)
                    score = result["evaluation"]["score"]
                    print(f"    ✅ Evaluated: Score {score}/10, {result.get('tokens_used', 0)} tokens")
            else:
                results["failed"].append((record_id, result["error"]))
                print(f"    ❌ Failed: {result['error']}")
            
            # Rate limiting - small delay between requests
            time.sleep(0.5)
        
        return {**results, "total_tokens": total_tokens}

# ===================================