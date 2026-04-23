# File Encryption Tool

AES-256 file encryption from the command line. Written in Python.

## Usage

```bash
# Encrypt
python encrypt_tool.py --encrypt --input myfile.pdf --output myfile.enc

# Decrypt
python encrypt_tool.py --decrypt --input myfile.enc --output myfile.pdf
```

You'll be prompted for a password. Encrypting asks twice to prevent typos.

## How it works

| Module | Role |
|---|---|
| `crypto_engine.py` | AES-256-GCM encryption/decryption |
| `file_format.py` | 33-byte file header for format validation |
| `errors.py` | Clean error messages, no raw tracebacks |
| `encrypt_tool.py` | CLI entry point |

**Key decisions:**
- **AES-256-GCM** — encrypts and authenticates simultaneously; wrong password or tampered file fails immediately
- **PBKDF2 + 600k SHA-256 rounds** — NIST 2023 recommendation; brute force impractical, real user under 1s
- **Fresh salt (16B) + IV (12B) per encrypt** — same file + same password → different output every time

## Setup

```bash
pip install cryptography      # install dep
pip install -e .              # optional: install globally as `encrypt`
pytest tests/                 # run test suite
```
