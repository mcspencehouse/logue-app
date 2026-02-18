import os
import logging
from cryptography.fernet import Fernet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_secrets():
    """
    Ensures that necessary secrets exist in the environment or a .env file.
    If ENCRYPTION_KEY is missing, generates a new one and saves it to .env.
    """
    env_file = ".env"
    
    # Load existing content to check for keys
    existing_content = ""
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            existing_content = f.read()

    updates = []
    
    # 1. Encryption Key
    # Check if ENCRYPTION_KEY is in the file (to avoid overwriting user's key if they set it externally but not in file, 
    # though usually we want file persistence)
    # Also check os.environ just in case it's set there but not in file? 
    # The goal is to create the file if it doesn't exist.
    
    if "ENCRYPTION_KEY=" not in existing_content:
        logger.info("Generating new ENCRYPTION_KEY...")
        key = Fernet.generate_key().decode()
        updates.append(f"ENCRYPTION_KEY={key}")
        # Set in current process for immediate use
        os.environ["ENCRYPTION_KEY"] = key
        
    # 2. Honda Client Secret
    # Use known default for the client ID if not present
    if "HONDA_CLIENT_SECRET=" not in existing_content:
        logger.info("Setting default HONDA_CLIENT_SECRET...")
        # WARNING: This is a default client secret for the Honda/Acura mobile app.
        # It is theoretically public but should be treated with care.
        # If you have your own, please set HONDA_CLIENT_SECRET in your .env file or environment.
        default_secret = "q4w5hzeqkFVMPQaeKuil"
        updates.append(f"HONDA_CLIENT_SECRET={default_secret}")
        if "HONDA_CLIENT_SECRET" not in os.environ:
             os.environ["HONDA_CLIENT_SECRET"] = default_secret

    # Write updates to .env
    if updates:
        mode = "a" if os.path.exists(env_file) else "w"
        try:
            with open(env_file, mode) as f:
                if mode == "a" and existing_content and not existing_content.endswith("\n"):
                    f.write("\n")
                for update in updates:
                    f.write(f"{update}\n")
            logger.info(f"Updated {env_file} with new secrets.")
        except IOError as e:
            logger.error(f"Failed to write to {env_file}: {e}")
    else:
        logger.debug("Secrets already exist in .env or are not needed.")

if __name__ == "__main__":
    ensure_secrets()
