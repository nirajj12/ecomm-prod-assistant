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
        STRICT RULES:
        - Answer ONLY using the information provided in the CONTEXT.
        - The CONTEXT comes from our internal product catalog and reviews.
        - Do NOT use outside knowledge.
        - Do NOT guess, assume, or speculate.
        - If the CONTEXT does not contain enough information to answer the question, say:
        "This product information is not available in our catalog."
        ROLE:
        You are an expert EcommerceBot specialized in product recommendations and handling customer queries.
        Analyze the provided product titles, ratings, and reviews to provide accurate, helpful responses.
        Stay relevant to the context, and keep your answers concise and informative.
        

        INSTRUCTIONS:
        - Use product reviews to judge quality, value for money, and user experience.
        - Use metadata such as price and rating when present.
        - Keep answers concise, factual, and helpful.
        - Do NOT mention that you are an AI or language model.

        CONTEXT:
        {context}

        QUESTION: {question}

        YOUR ANSWER:
        """,
        description="Handles ecommerce QnA & product recommendation flows"
    )
}