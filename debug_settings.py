
import os
import sys
# Add current directory to path
sys.path.append(os.getcwd())

from app.core.config import settings
print(f"GITHUB_CLIENT_ID: '{settings.GITHUB_CLIENT_ID}'")
print(f"GITHUB_REDIRECT_URI: '{settings.GITHUB_REDIRECT_URI}'")
