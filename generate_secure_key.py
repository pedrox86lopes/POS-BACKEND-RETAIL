import os
import secrets # Recommended for cryptographic

# For Flask's SECRET_KEY, a string of 32 bytes (64 hex characters) is a good start
print(secrets.token_hex(32))