"""
file_format.py — Custom .enc file format handler
==================================================
Defines the binary structure of encrypted files produced by this tool.

File layout:
    [4 bytes magic] [1 byte version] [16 bytes salt] [12 bytes IV] [ciphertext + 16 byte GCM tag]

Magic bytes : b'AES\x00'  — lets us identify our files and reject random binary blobs
Version byte: 0x01        — allows future format changes without breaking old files

This module wraps crypto_engine.py and adds the header layer on top.
"""

import os
import sys
import struct
from cryptography.exceptions import InvalidTag

from crypto_engine import derive_key, SALT_SIZE, IV_SIZE
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ── Format constants ──────────────────────────────────────────────────────────

MAGIC        = b'AES\x00'   # 4 bytes — identifies this as our encrypted file
VERSION      = 0x01         # 1 byte  — file format version
HEADER_SIZE  = len(MAGIC) + 1 + SALT_SIZE + IV_SIZE  # 4+1+16+12 = 33 bytes


# ── Write encrypted file ──────────────────────────────────────────────────────

def write_enc_file(output_path: str, salt: bytes, iv: bytes, ciphertext: bytes) -> None:
    """
    Write a fully formatted .enc file to disk.

    Layout:
        magic (4B) | version (1B) | salt (16B) | iv (12B) | ciphertext+tag

    Args:
        output_path: Where to write the file.
        salt:        16 random bytes used for key derivation.
        iv:          12 random bytes used as GCM nonce.
        ciphertext:  Encrypted bytes including the 16-byte GCM auth tag.
    """
    with open(output_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("B", VERSION))  # single unsigned byte
        f.write(salt)
        f.write(iv)
        f.write(ciphertext)


# ── Read encrypted file ───────────────────────────────────────────────────────

def read_enc_file(input_path: str) -> tuple[int, bytes, bytes, bytes]:
    """
    Read and validate a .enc file, returning its components.

    Raises:
        ValueError: If the file is not a valid .enc file (bad magic, too short, etc.)

    Returns:
        (version, salt, iv, ciphertext)
    """
    with open(input_path, "rb") as f:
        data = f.read()

    # Check minimum size
    if len(data) < HEADER_SIZE + 1:
        raise ValueError(
            f"File is too small to be a valid .enc file ({len(data)} bytes)."
        )

    # Validate magic bytes
    magic = data[:4]
    if magic != MAGIC:
        raise ValueError(
            "This does not appear to be a valid .enc file (bad magic bytes).\n"
            "Make sure you are decrypting a file that was encrypted with this tool."
        )

    # Read version
    version = struct.unpack("B", data[4:5])[0]
    if version != VERSION:
        raise ValueError(
            f"Unsupported file format version: {version}. "
            f"This tool supports version {VERSION}."
        )

    # Split out salt, IV, ciphertext
    offset = 5
    salt       = data[offset: offset + SALT_SIZE];  offset += SALT_SIZE
    iv         = data[offset: offset + IV_SIZE];     offset += IV_SIZE
    ciphertext = data[offset:]

    return version, salt, iv, ciphertext


# ── High-level encrypt / decrypt with format ──────────────────────────────────

def encrypt_file_v2(input_path: str, output_path: str, password: str) -> None:
    """
    Encrypt a file and write it in the versioned .enc format.

    Args:
        input_path:  Path to any plaintext file.
        output_path: Where to write the .enc file.
        password:    User-supplied password.
    """
    with open(input_path, "rb") as f:
        plaintext = f.read()

    salt = os.urandom(SALT_SIZE)
    iv   = os.urandom(IV_SIZE)
    key  = derive_key(password, salt)

    aesgcm     = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, plaintext, None)

    write_enc_file(output_path, salt, iv, ciphertext)


def decrypt_file_v2(input_path: str, output_path: str, password: str) -> None:
    """
    Decrypt a .enc file written by encrypt_file_v2().

    Raises:
        ValueError:  If the file header is invalid or version is unsupported.
        InvalidTag:  If the password is wrong or the file has been tampered with.

    Args:
        input_path:  Path to the .enc file.
        output_path: Where to write the decrypted file.
        password:    The password used during encryption.
    """
    version, salt, iv, ciphertext = read_enc_file(input_path)

    key    = derive_key(password, salt)
    aesgcm = AESGCM(key)

    plaintext = aesgcm.decrypt(iv, ciphertext, None)

    with open(output_path, "wb") as f:
        f.write(plaintext)


# ── Self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    print("Running file_format self-test...\n")

    password = "test-password-123"
    original = b"Top secret data! " * 200

    with tempfile.TemporaryDirectory() as tmpdir:
        enc_path = os.path.join(tmpdir, "test.enc")
        out_path = os.path.join(tmpdir, "test_recovered.bin")

        # Encrypt
        encrypt_file_v2.__doc__  # just a reference to avoid unused import warning
        salt = os.urandom(SALT_SIZE)
        iv   = os.urandom(IV_SIZE)
        key  = derive_key(password, salt)
        ct   = AESGCM(key).encrypt(iv, original, None)
        write_enc_file(enc_path, salt, iv, ct)

        # Check file size
        file_size = os.path.getsize(enc_path)
        expected_overhead = HEADER_SIZE + 16  # header + GCM tag
        print(f"  Original size  : {len(original)} bytes")
        print(f"  Encrypted size : {file_size} bytes")
        print(f"  Header overhead: {HEADER_SIZE} bytes (magic + version + salt + IV)")
        print(f"  GCM tag        : 16 bytes")
        print(f"  Total overhead : {file_size - len(original)} bytes")

        # Validate magic bytes in file
        with open(enc_path, "rb") as f:
            raw = f.read(5)
        assert raw[:4] == MAGIC, "FAIL: Magic bytes not written correctly"
        assert raw[4] == VERSION, "FAIL: Version byte not written correctly"
        print(f"\n  Magic bytes check : PASS ({MAGIC})")
        print(f"  Version byte check: PASS (version={VERSION})")

        # Read back and decrypt
        v, s, i, c = read_enc_file(enc_path)
        recovered = AESGCM(derive_key(password, s)).decrypt(i, c, None)
        assert recovered == original, "FAIL: Decrypted data does not match original"
        print(f"  Roundtrip decrypt : PASS")

        # Test bad magic rejection
        with open(enc_path, "rb") as f:
            corrupted = b'XXXX' + f.read()[4:]
        bad_path = os.path.join(tmpdir, "bad.enc")
        with open(bad_path, "wb") as f:
            f.write(corrupted)
        try:
            read_enc_file(bad_path)
            print("  FAIL: Bad magic was not rejected!")
            sys.exit(1)
        except ValueError as e:
            print(f"  Bad magic rejected: PASS")

    print("\nAll tests passed.")