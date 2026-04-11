# File-Encryption-tool
This is a tool that can  that can encrypt and decrypt any file using Aes-256 with a password.

Step 1  Core encryption engine
What this file does
crypto_engine.py is the cryptographic heart of the tool.
It handles everything related to turning bytes into encrypted bytes (and back).
It knows nothing about the CLI, file formats, or the user interface  those come in later steps.

Functions at a glance
FunctionWhat it doesderive_key(password, salt)Turns a password + salt into a 256-bit AES keyencrypt_bytes(plaintext, password)Encrypts raw bytes, returns salt + IV + ciphertextdecrypt_bytes(blob, password)Reverses encrypt_bytes; raises on bad password or tampered dataencrypt_file(in, out, password)Reads a file, encrypts it, writes result to diskdecrypt_file(in, out, password)Reads an encrypted file, decrypts it, writes plaintext to disk

Security decisions explained
AES-256-GCM
AES (Advanced Encryption Standard) with a 256-bit key is the gold standard for symmetric encryption  used by governments and banks worldwide.
The GCM (Galois/Counter Mode) variant adds authenticated encryption: the decryption step automatically verifies that nobody has tampered with the file. If even a single byte has been changed or the password is wrong decryption raises InvalidTag immediately instead of returning garbage bytes. You get both confidentiality and integrity in one step.
PBKDF2-HMAC-SHA256 key derivation
Passwords are human-memorable but too short and predictable to use as raw keys.
PBKDF2 (Password-Based Key Derivation Function 2) runs the password + a salt through SHA-256 hashing 600,000 times. This means:

A correct password still derives the key in < 1 second on modern hardware.
An attacker brute-forcing passwords must spend 600,000× more time per guess.
600,000 iterations is the NIST SP 800-132 recommendation as of 2023.

Random salt (16 bytes)
The salt is a random value mixed into the key derivation. Storing a unique salt per file means:

Two files encrypted with the same password get different keys.
Pre-computed "rainbow table" attacks are useless.

The salt is not secret it is stored at the beginning of the encrypted output.
Random IV / nonce (12 bytes)
The Initialization Vector (IV) randomises the encryption even when the plaintext is identical. Without it, encrypting the same file twice would produce the same ciphertext, leaking information.
12 bytes is the recommended GCM nonce size. Like the salt, the IV is not secret and is stored in the output.
Output layout
┌─────────────┬──────────────┬──────────────────────────────────────┐
│  salt       │  IV          │  ciphertext  +  GCM auth tag (16 B)  │
│  16 bytes   │  12 bytes    │  (same length as plaintext) + 16 B   │
└─────────────┴──────────────┴──────────────────────────────────────┘
Total overhead: 44 bytes per encrypted file (16 + 12 + 16).

Dependencies
pip install cryptography
The cryptography package is maintained by the Python Cryptographic Authority (PyCA) and is the de-facto standard for production cryptography in Python.

Running the self-test
bashpython crypto_engine.py
Expected output:
Running crypto_engine self-test...

  Original size :     3300 bytes
  Encrypted size:     3344 bytes  (+44 bytes overhead)
  Decrypt (correct password): PASS
  Decrypt (wrong password)  : PASS — correctly rejected
  Randomness check          : PASS — each encryption is unique

All tests passed.


# Step 2 — CLI interface

## Usage

Always run from inside your project folder using the venv Python:

### Encrypt a file
```powershell
venv\Scripts\python.exe encrypt_tool.py --encrypt --input myfile.pdf --output myfile.pdf.enc
```

### Decrypt a file
```powershell
venv\Scripts\python.exe encrypt_tool.py --decrypt --input myfile.pdf.enc --output myfile.pdf
```

### See all options
```powershell
venv\Scripts\python.exe encrypt_tool.py --help
```

---

## What happens when you encrypt

1. You provide `--input` and `--output` paths
2. Tool prompts for a password (hidden — nothing shows on screen)
3. Tool asks you to confirm the password
4. File is encrypted and saved
5. You see input/output sizes and time taken

## What happens when you decrypt

1. You provide `--input` and `--output` paths
2. Tool prompts for the password
3. If the password is correct → file is decrypted and saved
4. If the password is wrong → error message, no output file left behind

---

## Flags reference

| Flag | Required | Description |
|---|---|---|
| `--encrypt` | one of these two | Encrypt mode |
| `--decrypt` | one of these two | Decrypt mode |
| `--input FILE` | yes | Path to the file to read |
| `--output FILE` | yes | Path to write the result |

---

## Example session

```
PS C:\Users\tette\OneDrive\Desktop\Fle_encryption>
venv\Scripts\python.exe encrypt_tool.py --encrypt --input secret.pdf --output secret.pdf.enc

  Encrypting: secret.pdf
  Output    : secret.pdf.enc

  Enter password    :
  Confirm password  :

  Done in 0.43s
  Input size : 2.1 MB
  Output size: 2.1 MB

  File encrypted successfully.
```

---

## What's next

| Step | What we'll add |
|---|---|
| Step 3 | Custom `.enc` file format with a magic header and version byte |
| Step 4 | Better error handling — distinguish wrong password vs. corrupted file |
| Step 5 | Full test suite and packaging so the tool installs globally |
