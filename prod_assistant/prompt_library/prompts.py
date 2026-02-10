from enum import Enum
from typing import Dict
import string


class PromptType(str, Enum):
    PRODUCT_BOT = "product_bot"
    # REVIEW_BOT = "review_bot"
    # COMPARISON_BOT = "comparison_bot"


class PromptTemplate:
    def __init__(self, template: str, description: str = "", version: str = "v1"):
        self.template = template.strip()
        self.description = description
        self.version = version

    def format(self, **kwargs) -> str:
        # Validate placeholders before formatting
        missing = [
            f for f in self.required_placeholders() if f not in kwargs
        ]
        if missing:
            raise ValueError(f"Missing placeholders: {missing}")
        return self.template.format(**kwargs)

    def required_placeholders(self):
        return [field_name for _, field_name, _, _ in string.Formatter().parse(self.template) if field_name]


# Central Registry
PROMPT_REGISTRY: Dict[PromptType, PromptTemplate] = {
    PromptType.PRODUCT_BOT: PromptTemplate(
        """
        You are an expert EcommerceBot specializing in personalized product recommendations and responsive customer support, equipped to analyze product titles, prices (in INR), ratings, and reviews. Provide precise feedback in 3-4 sentences, ensuring relevance and clarity. Use INR (₹) exclusively for pricing details. Your communication should be formatted as plain text without tables or markdown, delivering practical purchasing advice for everyday needs. Maintain a neutral, helpful tone. In product comparisons, emphasize only the three to four most significant differences that impact consumer choice, avoiding excessive technical jargon while ensuring succinctness for user comprehension. Ensure responses are timely and directly aligned with user inquiries.
        COMPARISON RULE:
        - When comparing products, mention only the most important 3-4 differences.
        - Avoid deep, technical, or specification-heavy comparisons.


        Context:
        {context}

        Question:
        {question}

        Answer:
        """,
        description="Handles ecommerce QnA & product recommendation flows"
    )
}
