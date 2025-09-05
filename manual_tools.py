
import argparse
import json
from processors.decompressor import DataDecompressor
from processors.compressor import DataCompressor
from processors.llm_evaluator import LLMEvaluator
from utils.airtable_client import airtable

class ManualTools:
    def __init__(self):
        self.decompressor = DataDecompressor()
        self.compressor = DataCompressor()
        self.llm_evaluator = LLMEvaluator()
        self.client = airtable
    
    def decompress_for_editing(self, applicant_id):
        """Decompress applicant data for manual editing"""
        print(f"🔧 Decompressing applicant {applicant_id} for manual editing...")
        
        result = self.decompressor.decompress_applicant_data(applicant_id)
        
        if result["success"]:
            print("✅ Successfully decompressed data into child tables")
            print("📝 You can now edit the data in Airtable interface:")
            print(f"   • Personal Details table")
            print(f"   • Work Experience table")
            print(f"   • Salary Preferences table")
            print(f"💡 After editing, run: python manual_tools.py reprocess --applicant {applicant_id}")
            return True
        else:
            print(f"❌ Failed to decompress: {result['error']}")
            return False
    
    def reprocess_after_edit(self, applicant_id):
        """Recompress and re-evaluate after manual edits"""
        print(f"🔄 Reprocessing applicant {applicant_id} after manual edits...")
        
        # Step 1: Recompress
        print("  📦 Step 1: Recompressing data...")
        compress_result = self.compressor.compress_applicant_data(applicant_id)
        
        if not compress_result["success"]:
            print(f"  ❌ Compression failed: {compress_result['error']}")
            return False
        
        print("  ✅ Data recompressed successfully")
        
        # Step 2: Re-evaluate with LLM
        print("  🤖 Step 2: Re-evaluating with LLM...")
        applicant_record = self.client.get_applicant(applicant_id)
        llm_result = self.llm_evaluator.evaluate_applicant(applicant_record)
        
        if llm_result["success"] and not llm_result.get("skipped"):
            score = llm_result["evaluation"]["score"]
            print(f"  ✅ LLM re-evaluation complete: Score {score}/10")
        elif llm_result.get("skipped"):
            print(f"  ⏭️  LLM evaluation skipped: {llm_result['reason']}")
        else:
            print(f"  ❌ LLM evaluation failed: {llm_result['error']}")
        
        print("✅ Reprocessing complete")
        return True
    
    def view_applicant_summary(self, applicant_id):
        """Display comprehensive applicant summary"""
        print(f"📋 Applicant Summary: {applicant_id}")
        print("=" * 50)
        
        try:
            applicant = self.client.get_applicant(applicant_id)
            fields = applicant.get("fields", {})
            
            # Basic info
            print("📊 BASIC INFO:")
            compressed_json = fields.get("Compressed JSON")
            if compressed_json:
                data = json.loads(compressed_json)
                personal = data.get("personal", {})
                print(f"  • Name: {personal.get('name', 'N/A')}")
                print(f"  • Location: {personal.get('location', 'N/A')}")
                print(f"  • Email: {personal.get('email', 'N/A')}")
                
                # Experience summary
                experience = data.get("experience", [])
                print(f"\n💼 EXPERIENCE ({len(experience)} roles):")
                for exp in experience:
                    print(f"  • {exp.get('title', 'N/A')} at {exp.get('company', 'N/A')}")
                
                # Salary info
                salary = data.get("salary", {})
                if salary:
                    rate = salary.get("preferred_rate", "N/A")
                    currency = salary.get("currency", "")
                    hours = salary.get("availability", "N/A")
                    print(f"\n💰 COMPENSATION:")
                    print(f"  • Preferred Rate: {rate} {currency}/hour")
                    print(f"  • Availability: {hours} hours/week")
            
            # Pipeline status
            print(f"\n🔄 PIPELINE STATUS:")
            print(f"  • Compressed JSON: {'✅' if fields.get('Compressed JSON') else '❌'}")
            print(f"  • Shortlist Status: {fields.get('Shortlist Status', 'Not evaluated')}")
            print(f"  • LLM Summary: {'✅' if fields.get('LLM Summary') else '❌'}")
            if fields.get("LLM Score"):
                print(f"  • LLM Score: {fields.get('LLM Score')}/10")
            
            # LLM insights
            if fields.get("LLM Summary"):
                print(f"\n🤖 LLM INSIGHTS:")
                print(f"  • Summary: {fields.get('LLM Summary')}")
                if fields.get("LLM Issues"):
                    print(f"  • Issues: {fields.get('LLM Issues')}")
                if fields.get("LLM Follow-Ups"):
                    print(f"  • Follow-ups: {fields.get('LLM Follow-Ups')}")
            
        except Exception as e:
            print(f"❌ Error retrieving applicant data: {e}")
    
    def list_recent_applicants(self, limit=10):
        """List recent applicants with basic info"""
        print(f"📋 Recent Applicants (last {limit})")
        print("=" * 60)
        
        applicants = self.client.get_all_applicants()
        
        # Sort by creation date if available, otherwise just take first N
        recent_applicants = applicants[-limit:] if len(applicants) > limit else applicants
        
        for applicant in recent_applicants:
            record_id = applicant["id"]
            fields = applicant.get("fields", {})
            
            # Try to get name from compressed JSON or fallback
            name = "Unknown"
            if fields.get("Compressed JSON"):
                try:
                    data = json.loads(fields["Compressed JSON"])
                    name = data.get("personal", {}).get("name", "Unknown")
                except:
                    pass
            
            status_indicators = []
            if fields.get("Compressed JSON"):
                status_indicators.append("📦")
            if fields.get("Shortlist Status") == "Shortlisted":
                status_indicators.append("⭐")
            if fields.get("LLM Summary"):
                status_indicators.append("🤖")
            
            status_str = "".join(status_indicators) if status_indicators else "⚪"
            print(f"  {status_str} {record_id}: {name}")

def main():
    parser = argparse.ArgumentParser(description="Manual Tools for Contractor Application Management")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Decompress command
    decompress_parser = subparsers.add_parser("decompress", help="Decompress applicant for editing")
    decompress_parser.add_argument("--applicant", required=True, help="Applicant record ID")
    
    # Reprocess command  
    reprocess_parser = subparsers.add_parser("reprocess", help="Reprocess after editing")
    reprocess_parser.add_argument("--applicant", required=True, help="Applicant record ID")
    
    # View command
    view_parser = subparsers.add_parser("view", help="View applicant summary")
    view_parser.add_argument("--applicant", required=True, help="Applicant record ID")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List recent applicants")
    list_parser.add_argument("--limit", type=int, default=10, help="Number of applicants to show")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    tools = ManualTools()
    
    try:
        if args.command == "decompress":
            tools.decompress_for_editing(args.applicant)
        elif args.command == "reprocess":
            tools.reprocess_after_edit(args.applicant)
        elif args.command == "view":
            tools.view_applicant_summary(args.applicant)
        elif args.command == "list":
            tools.list_recent_applicants(args.limit)
    
    except Exception as e:
        print(f"💥 Command failed: {e}")
        exit(1)

if __name__ == "__main__":
    main()