from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
import json

def classify_and_route_ticket(ticket_text: str) -> dict:
    """
    Classifies a support ticket and routes it to the appropriate department.
    
    Args:
        ticket_text: The raw support ticket message from the customer.
    
    Returns:
        A dictionary with category, priority, department, and recommended_action.
    """
    # This function is a structured output helper that gets called by the agent.
    # The actual classification logic is handled by the LLM via the agent's instruction.
    return {"ticket_received": ticket_text}


classify_tool = FunctionTool(func=classify_and_route_ticket)

AGENT_INSTRUCTION = """
You are a support ticket classification and routing agent for a SaaS company.

When given a customer support ticket, you must analyze it and return ONLY a valid JSON object with no additional text, explanation, or markdown formatting.

The JSON must have exactly these fields:
- "category": one of ["Billing", "Technical", "General", "Refund", "Account"]
- "priority": one of ["Low", "Medium", "High", "Critical"]
- "department": the team that should handle it
- "recommended_action": a short, actionable instruction for the support team (1-2 sentences)
- "confidence": one of ["low", "medium", "high"]
- "summary": a one-sentence summary of the customer's issue

Priority guidelines:
- Critical: Service is completely down, data loss, security breach
- High: Major feature broken, payment issues, account locked
- Medium: Feature partially broken, billing confusion, slow performance
- Low: General questions, feature requests, cosmetic issues

Department routing:
- Billing → "Finance & Billing Team"
- Technical → "Engineering Support Team"
- Refund → "Finance & Billing Team"
- Account → "Account Management Team"
- General → "Customer Success Team"

Return ONLY the JSON object. No preamble, no explanation, no markdown.
"""

root_agent = LlmAgent(
    name="support_ticket_classifier",
    model="gemini-2.5-flash",
    instruction=AGENT_INSTRUCTION,
    description="Classifies and routes customer support tickets to the appropriate department with priority levels.",
)
