# prod_assistant/utils/runtime.py

import os
import logging
import warnings

# ----------------------------
# Hugging Face / Transformers
# ----------------------------
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["HF_HUB_VERBOSITY"] = "error"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ----------------------------
# Logging silence
# ----------------------------
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)

# ----------------------------
# Python warnings (HF uses these)
# ----------------------------
warnings.filterwarnings(
    "ignore",
    message=".*UNEXPECTED.*",
    category=UserWarning,
)

warnings.filterwarnings(
    "ignore",
    category=FutureWarning,
    module="sentence_transformers",
)
