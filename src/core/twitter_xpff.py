"""
Twitter X-Xp-Forwarded-For Header Generator

Generates the X-Xp-Forwarded-For (XPFF) header that Twitter uses for anti-bot detection.
Based on reverse engineering work from: https://github.com/yeahyesfine/twitter-x-xp-forwarded-for-header

The XPFF header is generated via WASM on Twitter's frontend and uses:
- AES encryption with key derived from SHA-256(base_key + guest_id)
- Payload contains user agent, timestamp, and navigator properties
- Header is valid for 5 minutes (300,000 ms)
"""

import json
import time
import hashlib
import base64
import logging
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# Try to import pycryptodome, fall back gracefully if not available
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    CRYPTO_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ pycryptodome not installed. XPFF header generation disabled.")
    logger.warning("   Install with: pip install pycryptodome")
    CRYPTO_AVAILABLE = False


class XPFFHeaderGenerator:
    """Generates the X-Xp-Forwarded-For header for Twitter requests."""
    
    # Hardcoded base key from Twitter's WASM (as of early 2025)
    # This key is static and embedded in their frontend code
    DEFAULT_BASE_KEY = "0e6be1f1e21ffc33590b888fd4dc81b19713e570e805d4e5df80a493c9571a05"
    
    def __init__(self, base_key: str = None):
        """
        Initialize the XPFF generator.
        
        Args:
            base_key: The base key for encryption. Uses default if not provided.
        """
        self.base_key = base_key or self.DEFAULT_BASE_KEY
    
    def _derive_key(self, guest_id: str) -> bytes:
        """Derive AES key from base_key + guest_id using SHA-256."""
        # Decode URL-encoded guest_id if necessary
        decoded_guest_id = unquote(guest_id)
        combined = self.base_key + decoded_guest_id
        return hashlib.sha256(combined.encode()).digest()
    
    def generate_xpff(self, user_agent: str, guest_id: str) -> str:
        """
        Generate the X-Xp-Forwarded-For header value.
        
        Args:
            user_agent: The browser user agent string
            guest_id: The guest_id from Twitter cookies (URL-encoded)
            
        Returns:
            The encrypted XPFF header value, or empty string if crypto unavailable
        """
        if not CRYPTO_AVAILABLE:
            return ""
        
        try:
            # Create the payload
            payload = {
                "navigator_properties": {
                    "hasBeenActive": "true",
                    "userAgent": user_agent,
                    "webdriver": "false"
                },
                "created_at": int(time.time() * 1000)  # Timestamp in milliseconds
            }
            
            payload_json = json.dumps(payload, separators=(',', ':'))
            
            # Derive key and encrypt
            key = self._derive_key(guest_id)
            cipher = AES.new(key, AES.MODE_CBC)
            
            # Pad and encrypt
            padded_data = pad(payload_json.encode(), AES.block_size)
            encrypted = cipher.encrypt(padded_data)
            
            # Combine IV and encrypted data, then base64 encode
            result = base64.b64encode(cipher.iv + encrypted).decode()
            
            logger.debug(f"Generated XPFF header (valid for 5 minutes)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate XPFF header: {e}")
            return ""
    
    def decode_xpff(self, encrypted_value: str, guest_id: str) -> str:
        """
        Decode an existing XPFF header value (for debugging).
        
        Args:
            encrypted_value: The base64-encoded XPFF header
            guest_id: The guest_id used for encryption
            
        Returns:
            The decrypted payload as a string
        """
        if not CRYPTO_AVAILABLE:
            return ""
        
        try:
            # Decode base64
            data = base64.b64decode(encrypted_value)
            
            # Extract IV (first 16 bytes) and ciphertext
            iv = data[:16]
            ciphertext = data[16:]
            
            # Derive key and decrypt
            key = self._derive_key(guest_id)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            
            decrypted = unpad(cipher.decrypt(ciphertext), AES.block_size)
            return decrypted.decode()
            
        except Exception as e:
            logger.error(f"Failed to decode XPFF header: {e}")
            return ""


def get_xpff_header(user_agent: str, guest_id: str) -> dict:
    """
    Convenience function to get the XPFF header as a dict.
    
    Args:
        user_agent: The browser user agent string
        guest_id: The guest_id from Twitter cookies
        
    Returns:
        Dict with the header, or empty dict if generation fails
    """
    generator = XPFFHeaderGenerator()
    value = generator.generate_xpff(user_agent, guest_id)
    
    if value:
        return {"X-Xp-Forwarded-For": value}
    return {}
