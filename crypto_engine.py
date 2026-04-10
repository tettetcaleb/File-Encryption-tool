"""
crypto_engine.py — AES-256-GCM encryption/decryption core
=============================================================
This module contains the pure cryptographic logic for the tool.
It does NOT handle CLI, file formats, or error display — those come in later steps.

Security choices:
  - AES-256-GCM     : authenticated encryption; detects tampering automatically
  - PBKDF2-HMAC-SHA256 : key derivation from password; 600,000 iterations (NIST 2023 rec.)
  - 16-byte salt    : random per encryption; stored with ciphertext
  - 12-byte IV/nonce: random per encryption; GCM standard size
  - 32-byte key     : 256-bit AES key derived from password + salt

Depends on:  pip install cryptography
"""

import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


#  Constants

SALT_SIZE   = 16   # bytes  — random per file, stored in output
IV_SIZE     = 12   # bytes  — GCM nonce, random per file, stored in output
KEY_SIZE    = 32   # bytes  — 256-bit AES key
KDF_ITERS   = 600_000  # PBKDF2 iterations (NIST SP 800-132 recommendation, 2023)


#  Key derivation 

def derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit AES key from a plaintext password and a random salt.

    Uses PBKDF2-HMAC-SHA256 with 600,000 iterations.
    The salt must be stored alongside the ciphertext so decryption can
    reproduce the exact same key.

    Args:
        password: The user-supplied plaintext password.
        salt:     16 random bytes generated at encrypt time.

    Returns:
        32-byte key suitable for AES-256.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=KDF_ITERS,
    )
    return kdf.derive(password.encode("utf-8"))


#  Encrypt

def encrypt_bytes(plaintext: bytes, password: str) -> bytes:
    """
    Encrypt arbitrary bytes with AES-256-GCM using a password.

    Generates a fresh random salt and IV on every call so that encrypting
    the same file twice with the same password produces different output.

    Output layout (all fields are concatenated, no delimiters):
        [16 bytes salt] [12 bytes IV] [ciphertext + 16-byte GCM auth tag]

    The GCM auth tag is appended automatically by the cryptography library.
    It protects both the ciphertext and any additional authenticated data
    (we don't use AAD here, but GCM still authenticates the ciphertext itself).

    Args:
        plaintext: Raw bytes of any file.
        password:  User-supplied password string.

    Returns:
        Encrypted blob: salt + IV + ciphertext+tag
    """
    salt = os.urandom(SALT_SIZE)
    iv   = os.urandom(IV_SIZE)
    key  = derive_key(password, salt)

    aesgcm     = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext, None)  # None = no AAD

    return salt + iv + ciphertext


# ─

def decrypt_bytes(blob: bytes, password: str) -> bytes:
    """
    Decrypt a blob produced by encrypt_bytes().

    Splits the blob into salt / IV / ciphertext+tag, re-derives the key,
    then authenticates and decrypts in one step.

    If the password is wrong OR the file has been tampered with, AESGCM
    raises cryptography.exceptions.InvalidTag. The caller is responsible
    for catching that and showing a user-friendly message (Step 4).

    Args:
        blob:     Raw bytes as returned by encrypt_bytes().
        password: The same password used to encrypt.

    Returns:
        Decrypted plaintext bytes.

    Raises:
        ValueError: If blob is too short to contain salt + IV.
        cryptography.exceptions.InvalidTag: If password is wrong or data is corrupt.
    """
    min_size = SALT_SIZE + IV_SIZE
    if len(blob) < min_size:
        raise ValueError(
            f"Data is too short to be a valid encrypted file "
            f"(got {len(blob)} bytes, need at least {min_size})."
        )

    salt       = blob[:SALT_SIZE]
    iv         = blob[SALT_SIZE:SALT_SIZE + IV_SIZE]
    ciphertext = blob[SALT_SIZE + IV_SIZE:]

    key    = derive_key(password, salt)
    aesgcm = AESGCM(key)

    return aesgcm.decrypt(iv, ciphertext, None)


#  File helpers 
def encrypt_file(input_path: str, output_path: str, password: str) -> None:
    """
    Read a file, encrypt its contents, and write the encrypted blob to disk.

    Args:
        input_path:  Path to the plaintext file (any type).
        output_path: Path where the encrypted file will be written.
        password:    User-supplied password.
    """
    with open(input_path, "rb") as f:
        plaintext = f.read()

    encrypted = encrypt_bytes(plaintext, password)

    with open(output_path, "wb") as f:
        f.write(encrypted)


def decrypt_file(input_path: str, output_path: str, password: str) -> None:
    """
    Read an encrypted file, decrypt its contents, and write plaintext to disk.

    Args:
        input_path:  Path to the encrypted file.
        output_path: Path where the decrypted file will be written.
        password:    The password used during encryption.

    Raises:
        ValueError: If the file is too short / malformed.
        cryptography.exceptions.InvalidTag: If password is wrong or data is tampered.
    """
    with open(input_path, "rb") as f:
        blob = f.read()

    plaintext = decrypt_bytes(blob, password)

    with open(output_path, "wb") as f:
        f.write(plaintext)




if __name__ == "__main__":
    import sys

    print("Running crypto_engine self-test...\n")

    password  = "hunter2-but-longer-and-better!"
    original  = b"Hello, this is a secret message. " * 100

    # Encrypt
    blob = encrypt_bytes(original, password)
    print(f"  Original size : {len(original):>8} bytes")
    print(f"  Encrypted size: {len(blob):>8} bytes  (+{len(blob)-len(original)} bytes overhead)")

    # Decrypt with correct password
    recovered = decrypt_bytes(blob, password)
    assert recovered == original, "FAIL: decrypted bytes don't match original!"
    print("  Decrypt (correct password): PASS")

    # Attempt decrypt with wrong password
    from cryptography.exceptions import InvalidTag
    try:
        decrypt_bytes(blob, "wrong-password")
        print("  FAIL: wrong password was accepted — this should never happen!")
        sys.exit(1)
    except InvalidTag:
        print("  Decrypt (wrong password)  : PASS — correctly rejected")

    # Verify two encryptions of the same plaintext differ (random IV/salt)
    blob2 = encrypt_bytes(original, password)
    assert blob != blob2, "FAIL: two encryptions produced identical output — IV/salt not random!"
    print("  Randomness check          : PASS — each encryption is unique")

    print("\nAll tests passed.")
