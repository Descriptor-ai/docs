import json
import time
import requests
from typing import Dict, Optional, Any

class SalesforceDescriptorIntegration:
    def __init__(self, 
                 sf_domain: str,
                 sf_access_token: str,
                 descriptor_token: str,
                 sf_api_version: str = "v62.0"):
        """Initialize integration with credentials"""
        self.sf_base_url = f"https://name.my.salesforce.com/services/data/{sf_api_version}"
        self.descriptor_base_url = "https://demo.descriptor.ai/api/v1"
        self.sf_headers = {
            "Authorization": f"Bearer {sf_access_token}",
            "Content-Type": "application/json"
        }
        self.descriptor_headers = {
            "Authorization": f"Bearer {descriptor_token}",
            "Content-Type": "application/json"
        }

    def submit_audio_for_analysis(self, audio_url: str) -> str:
        """Submit audio file to Descriptor.AI for analysis"""
        endpoint = f"{self.descriptor_base_url}/offline/processing"
        
        payload = {
            "audio": {
                "uri": audio_url
            },
            "config": {
                "language_code": "en-US",
                "transcript_model": "descriptor-default",
                "emotions_model": "emotions",
                "emotions_alignment": False,
                "emotions_diarization": False,
                "emotions_sentiment": False,
                "sentiment_llm_provider": "azure",
                "channels": 1,
                "insights": {
                    "summary": {
                        "provider": "azure",
                        "prompt_customization": ""
                    },
                    "agent-actions": {
                        "provider": "azure",
                        "prompt_customization": ""
                    }
                },
                "metrics": [],
                "mandatory_stages": [
                    "sentiment",
                    "insights"
                ]
            }
        }

        print("Request payload:", json.dumps(payload, indent=2))

        response = requests.post(
            endpoint,
            headers=self.descriptor_headers,
            json=payload
        )

        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response body: {response.text}")

        if response.status_code != 200:
            print(f"API Error Response: {response.text}")
            response.raise_for_status()

        return response.json()["result_id"]

    def get_analysis_results(self, result_id: str, max_retries: int = 30) -> Dict[str, Any]:
        """Poll for analysis results"""
        endpoint = f"{self.descriptor_base_url}/offline/processing/{result_id}"
        
        for attempt in range(max_retries):
            response = requests.get(
                endpoint,
                headers=self.descriptor_headers
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 425:  # Still processing
                print(f"Attempt {attempt + 1}/{max_retries}: Still processing...")
                time.sleep(10)
            else:
                print(f"Error response: {response.text}")
                response.raise_for_status()
                
        raise TimeoutError("Analysis results not available after maximum retries")

    def create_salesforce_record(self, analysis_results: Dict[str, Any]) -> str:
        """Create a Call Analysis record in Salesforce"""
        endpoint = f"{self.sf_base_url}/sobjects/Call_Analysis__c"
        
        record = {
            "Name": f"Analysis_{analysis_results['job_id'][:10]}",
            "Summary_c__c": "\n".join(analysis_results.get("insights", {}).get("summary", [])),
            "Agent_Actions_c__c": json.dumps(analysis_results.get("insights", {}).get("agent_actions", [])),
        }

        print("Creating Salesforce record with data:", json.dumps(record, indent=2))

        response = requests.post(
            endpoint,
            headers=self.sf_headers,
            json=record
        )

        if response.status_code != 200:
            print(f"Salesforce Error Response: {response.text}")
            response.raise_for_status()

        return response.json()["id"]

    def process_call_recording(self, audio_url: str) -> str:
        """Process a call recording end-to-end"""
        try:
            # Submit audio for analysis
            result_id = self.submit_audio_for_analysis(audio_url)
            print(f"Analysis submitted. Job ID: {result_id}")
            
            # Get analysis results
            analysis_results = self.get_analysis_results(result_id)
            print("Analysis results received")
            
            # Create Salesforce record
            record_id = self.create_salesforce_record(analysis_results)
            print(f"Salesforce record created: {record_id}")
            
            return record_id
            
        except Exception as e:
            print(f"Error processing call recording: {str(e)}")
            raise

def main():
    # Initialize the integration with original values
    integration = SalesforceDescriptorIntegration(
        sf_domain="",
        sf_access_token="",
        descriptor_token=""
    )

    # Example usage with original audio URL
    try:
        audio_url = ""
        record_id = integration.process_call_recording(audio_url)
        print(f"Successfully created Salesforce record: {record_id}")

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()