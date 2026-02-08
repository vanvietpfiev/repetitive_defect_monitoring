"""
Script to generate password hash for streamlit-authenticator
Run this script to create new password hashes
"""

import streamlit_authenticator as stauth

# List of passwords you want to hash
passwords = ['vna1234']  # Replace with your desired password

# Generate hashes
hashed_passwords = stauth.Hasher(passwords).generate()

print("Generated password hashes:")
print("=" * 50)
for i, hash_pw in enumerate(hashed_passwords):
    print(f"Password {i+1}: {passwords[i]}")
    print(f"Hash: {hash_pw}")
    print("-" * 50)

print("\nCopy the hash and update it in app.py credentials dictionary")
