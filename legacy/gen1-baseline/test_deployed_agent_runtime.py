"""
test_deployed_agent_runtime.py: Connects directly to the live deployed MECopyrightComplianceAgent
on Google Cloud Agent Runtime (`ReasoningEngine 737568342830743552`) and executes a live cloud audit query.
"""

import vertexai
from vertexai.preview import reasoning_engines

PROJECT_ID = "your-gcp-project-id"
LOCATION = "us-central1"
RESOURCE_NAME = "projects/YOUR_PROJECT_NUMBER/locations/us-central1/reasoningEngines/YOUR_ENGINE_ID"


def test_live_agent_runtime():
    print("================================================================================")
    print("🌐 CONNECTING TO DEPLOYED GOOGLE CLOUD AGENT RUNTIME")
    print(f"   Resource: {RESOURCE_NAME}")
    print("================================================================================\n")

    vertexai.init(project=PROJECT_ID, location=LOCATION)

    print("1. Binding live client to deployed serverless Agent Runtime...")
    remote_agent = reasoning_engines.ReasoningEngine(RESOURCE_NAME)
    print(f"  ✔ Client Bound! Target Display Name: {remote_agent.display_name}")

    test_prompt = """
Perform a formal legal clearance review on the following screenplay excerpt from a Boston drama:
"GERALD LAMBEAU enters the MIT faculty lounge carrying two cups of DUNKIN' DONUTS coffee. He meets with SEAN MAGUIRE."

Check:
1. Metropolitan Census frequency rule for living character names ('Gerald Lambeau', 'Sean Maguire').
2. Sponsor Exclusivity check: Primary Production Sponsor is STARBUCKS. Check for competitor coffee brand mentions.
"""

    print(f"\n2. Executing live `.query()` against deployed Agent Runtime on Google Cloud...")
    print(f"   Prompt sent to serverless container ->\n{test_prompt}\n")

    response = remote_agent.query(input=test_prompt)

    print("================================================================================")
    print("✅ LIVE DEPLOYED AGENT RUNTIME RESPONSE RECEIVED")
    print("================================================================================")
    print(response)
    print("================================================================================\n")


if __name__ == "__main__":
    test_live_agent_runtime()
