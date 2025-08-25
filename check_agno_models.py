#!/usr/bin/env python3
"""Check available Agno models."""

import pkgutil
import agno.models

print("Available Agno model modules:")
for importer, modname, ispkg in pkgutil.iter_modules(agno.models.__path__):
    print(f"  - agno.models.{modname}")
    
# Try to import specific models
try:
    from agno.models.google import Gemini
    print("\n✅ Google Gemini model available!")
except ImportError as e:
    print(f"\n❌ Google Gemini not available: {e}")

try:
    from agno.models.aws import Claude
    print("✅ AWS Claude model available!")
except ImportError as e:
    print(f"❌ AWS Claude not available: {e}")

try:
    from agno.models.openai import GPT
    print("✅ OpenAI GPT model available!")
except ImportError as e:
    print(f"❌ OpenAI GPT not available: {e}")

# Check for vertex AI
try:
    from agno.models.gcp import VertexAI
    print("✅ GCP VertexAI model available!")
except ImportError as e:
    print(f"❌ GCP VertexAI not available: {e}")