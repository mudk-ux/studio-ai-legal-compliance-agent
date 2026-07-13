"""Deploy the multi-agent workflow to Vertex AI Agent Engine.

    python deploy/deploy_multiagent.py
"""

from _common import deploy
from studio_compliance.agents.multiagent import create_app

if __name__ == "__main__":
    deploy(
        create_app(),
        display_name="studio-compliance-multiagent",
        description="M&E legal compliance — coordinator + specialist multi-agent workflow",
    )
