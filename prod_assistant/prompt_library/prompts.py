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
        You are an expert EcommerceBot specialized in product recommendations and handling customer queries.
        Analyze the provided product titles,prices(in inr), ratings, and reviews to provide accurate, helpful responses.
        Stay relevant to the context, and keep your answers concise and informative.
        STRICT OUTPUT RULES:
        - Respond in plain text only.
        - Do NOT use tables, markdown, headings, or bullet lists.
        - Keep the response concise (maximum 3–4 sentences).
        - If price is mentioned, use INR (₹) only.

        RESPONSE GUIDELINES:
        - Answer using the provided context.
        - If context is limited, give a reasonable, high-level response without guessing exact prices.
        - Focus on practical buying advice and real-world usage.
        - Keep the tone clear, neutral, and helpful.

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
