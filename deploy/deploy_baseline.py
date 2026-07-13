"""Deploy the baseline single-agent to Vertex AI Agent Engine.

    python deploy/deploy_baseline.py
"""

from _common import deploy
from studio_compliance.agents.baseline import create_app

if __name__ == "__main__":
    deploy(
        create_app(),
        display_name="studio-compliance-baseline",
        description="M&E legal compliance — baseline single-agent (audited pipeline tool)",
    )
