
import argparse
import datetime
from processors.compressor import DataCompressor
from processors.shortlister import ApplicantShortlister  
from processors.llm_evaluator import LLMEvaluator
from utils.airtable_client import airtable

class ContractorPipeline:
    def __init__(self):
        self.compressor = DataCompressor()
        self.shortlister = ApplicantShortlister()
        self.llm_evaluator = LLMEvaluator()
        self.client = airtable
    
    def get_applicants_for_processing(self, mode="new_only"):
        """Get applicants that need processing based on mode"""
        all_applicants = self.client.get_all_applicants()
        
        if mode == "all":
            return all_applicants
        elif mode == "new_only":
            return [a for a in all_applicants 
                   if not a.get("fields", {}).get("Compressed JSON")]
        elif mode == "changed":
            # Logic to detect changed records would go here
            # For now, return records without LLM evaluation
            return [a for a in all_applicants 
                   if a.get("fields", {}).get("Compressed JSON") and 
                   not a.get("fields", {}).get("LLM Summary")]
        else:
            return []
    
    def run_full_pipeline(self, mode="new_only", single_applicant=None):
        """Run the complete processing pipeline"""
        print("🚀 Starting Contractor Application Pipeline")
        print(f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Handle single applicant mode
        if single_applicant:
            print(f"🎯 Processing single applicant: {single_applicant}")
            applicants_to_process = [self.client.get_applicant(single_applicant)]
        else:
            # Get applicants to process
            applicants_to_process = self.get_applicants_for_processing(mode)
            print(f"📊 Found {len(applicants_to_process)} applicants to process (mode: {mode})")
        
        if not applicants_to_process:
            print("✅ No applicants need processing. Pipeline complete.")
            return {"message": "No work needed"}
        
        # Phase 1: Compression
        print("\n📦 PHASE 1: Data Compression")
        print("-" * 40)
        compression_results = self._run_compression_phase(applicants_to_process, mode)
        
        # Phase 2: Shortlisting (only for successfully compressed)
        print("\n⭐ PHASE 2: Shortlisting Evaluation") 
        print("-" * 40)
        shortlist_results = self._run_shortlisting_phase()
        
        # Phase 3: LLM Evaluation (only for successfully compressed)
        print("\n🤖 PHASE 3: LLM Evaluation")
        print("-" * 40)
        llm_results = self._run_llm_phase()
        # llm_results = {"success": [], "failed": [], "skipped": [], "total_tokens": 0}
        
        # Summary Report
        self._print_pipeline_summary(compression_results, shortlist_results, llm_results)
        
        return {
            "compression": compression_results,
            "shortlisting": shortlist_results,
            "llm_evaluation": llm_results,
            "pipeline_completed": datetime.datetime.now().isoformat()
        }
    
    def _run_compression_phase(self, applicants_to_process, mode):
        """Run the compression phase"""
        if mode == "all":
            # Force recompression for all
            results = {"success": [], "failed": [], "skipped": []}
            for applicant in applicants_to_process:
                record_id = applicant["id"]
                print(f"  📦 Recompressing applicant {record_id}")
                result = self.compressor.compress_applicant_data(record_id)
                
                if result["success"]:
                    results["success"].append(record_id)
                else:
                    results["failed"].append((record_id, result["error"]))
                    print(f"  ❌ Failed: {result['error']}")
        else:
            # Normal compression (skip existing)
            results = self.compressor.compress_all_applicants()
        
        print(f"  ✅ Compressed: {len(results['success'])}")
        print(f"  ❌ Failed: {len(results['failed'])}")  
        print(f"  ⏭️  Skipped: {len(results.get('skipped', []))}")
        
        return results
    
    def _run_shortlisting_phase(self):
        """Run the shortlisting phase"""
        results = self.shortlister.shortlist_all_applicants()
        
        print(f"  ✅ Shortlisted: {len(results['success'])}")
        print(f"  ❌ Failed: {len(results['failed'])}")
        print(f"  ⏭️  Ineligible: {len(results['ineligible'])}")
        
        # Show shortlisted candidates
        if results['success']:
            print("  🌟 Newly Shortlisted Candidates:")
            for record_id, reasons in results['success']:
                print(f"    • {record_id}: {'; '.join(reasons)}")
        
        return results
    
    def _run_llm_phase(self):
        """Run the LLM evaluation phase"""
        results = self.llm_evaluator.evaluate_all_applicants()
        
        print(f"  ✅ Evaluated: {len(results['success'])}")
        print(f"  ❌ Failed: {len(results['failed'])}")
        print(f"  ⏭️  Skipped: {len(results['skipped'])}")
        print(f"  🎯 Total Tokens Used: {results.get('total_tokens', 0)}")
        
        return results
    
    def _print_pipeline_summary(self, compression, shortlisting, llm):
        """Print final pipeline summary"""
        print("\n" + "=" * 60)
        print("📈 PIPELINE SUMMARY")
        print("=" * 60)
        print(f"Data Compression:")
        print(f"  • Successfully compressed: {len(compression['success'])}")
        print(f"  • Failed: {len(compression['failed'])}")
        print(f"  • Skipped: {len(compression.get('skipped', []))}")
        
        print(f"\nShortlisting:")
        print(f"  • New shortlisted candidates: {len(shortlisting['success'])}")
        print(f"  • Ineligible: {len(shortlisting['ineligible'])}")
        print(f"  • Errors: {len(shortlisting['failed'])}")
        
        print(f"\nLLM Evaluation:")
        print(f"  • Successfully evaluated: {len(llm['success'])}")  
        print(f"  • Failed: {len(llm['failed'])}")
        print(f"  • Skipped (no changes): {len(llm['skipped'])}")
        print(f"  • Total API tokens used: {llm.get('total_tokens', 0)}")
        
        print(f"\n✅ Pipeline completed at {datetime.datetime.now().strftime('%H:%M:%S')}")

def main():
    parser = argparse.ArgumentParser(description="Contractor Application Processing Pipeline")
    parser.add_argument("--mode", choices=["new_only", "changed", "all"], default="new_only",
                       help="Processing mode: new_only, changed, or all")
    parser.add_argument("--applicant", help="Process single applicant by record ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without doing it")
    
    args = parser.parse_args()
    
    pipeline = ContractorPipeline()
    
    if args.dry_run:
        applicants = pipeline.get_applicants_for_processing(args.mode)
        print(f"🔍 DRY RUN: Would process {len(applicants)} applicants")
        for applicant in applicants[:5]:  # Show first 5
            name = applicant.get("fields", {}).get("Name", "Unknown")
            print(f"  • {applicant['id']}: {name}")
        if len(applicants) > 5:
            print(f"  • ... and {len(applicants) - 5} more")
        return
    
    try:
        results = pipeline.run_full_pipeline(mode=args.mode, single_applicant=args.applicant)
        
        # Exit codes for automation
        if results.get("message") == "No work needed":
            exit(0)  # Success, no work
        elif any(results.get(phase, {}).get("failed", []) for phase in ["compression", "shortlisting", "llm_evaluation"]):
            exit(1)  # Some failures occurred
        else:
            exit(0)  # Success
            
    except Exception as e:
        print(f"💥 Pipeline failed with error: {e}")
        exit(2)  # Critical failure

if __name__ == "__main__":
    main()