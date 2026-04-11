# File Encryption Tool

A command-line tool that encrypts and decrypts any file using AES-256 and a password. Built in Python.

---

## Install the dependency

```powershell
venv\Scripts\pip.exe install cryptography
```

---

## How to use it

Encrypt a file:
```powershell
venv\Scripts\python.exe encrypt_tool.py --encrypt --input myfile.pdf --output myfile.enc
```

Decrypt it back:
```powershell
venv\Scripts\python.exe encrypt_tool.py --decrypt --input myfile.enc --output myfile.pdf
```

It'll ask for your password when you run it. On encrypt it asks twice so you don't lock yourself out with a typo.

> Always run with `venv\Scripts\python.exe`, not the VS Code play button. The play button uses the wrong Python.

---

## How the code is split up

I gave each file one job so nothing gets tangled together.

- `crypto_engine.py` — the actual AES-256 encryption and decryption
- `file_format.py` — adds a header to encrypted files so we can identify them later
- `errors.py` — catches every failure and explains it in plain English
- `encrypt_tool.py` — the CLI that ties everything together

---

## Step 1 — crypto_engine.py

This is where the cryptography happens. Password comes in, encrypted bytes come out.

I used AES-256-GCM because the GCM mode does two things at once  it encrypts the file and it authenticates it. That means if someone tampers with the file, or you type the wrong password, decryption fails immediately instead of silently returning garbage.

Passwords go through PBKDF2 with 600,000 rounds of SHA-256 before becoming a key. That's slow enough to make brute forcing impractical but still under a second for the real user. The 600k number is from NIST's 2023 recommendation.

Every encryption also generates a fresh random salt (16 bytes) and IV (12 bytes). This means encrypting the same file twice with the same password produces completely different output each time.

Run the self-test:
```powershell
venv\Scripts\python.exe crypto_engine.py
```

---

## Step 2 — encrypt_tool.py

Wraps the crypto in a CLI. Handles the password prompt, the overwrite warning, and shows you the file sizes and time when it's done.

---

## Step 3 — file_format.py

Before this, the encrypted output was just raw bytes with no way to tell if it was actually one of our files. Trying to decrypt the wrong file would crash with a confusing Python error.

Now every `.enc` file starts with a 33-byte header:

```
4 bytes  — magic "AES\x00" so we know it's our file
1 byte   — version number (currently 1)
16 bytes — salt
12 bytes — IV
the rest — encrypted data + 16-byte auth tag
```

Total overhead added to your file: 49 bytes.

Run the self-test:
```powershell
venv\Scripts\python.exe file_format.py
```

---

## Step 4 — errors.py

Before this, anything going wrong meant a Python traceback. Now every failure gives you one clean line explaining what happened and the partial output file gets cleaned up automatically so you're never left with broken files on disk.

Errors it handles: wrong password, file not found, not a valid .enc file, file corrupted, permission denied, disk full.

Run the self-test:
```powershell
venv\Scripts\python.exe errors.py
```

---

## Step 5 — tests and packaging

A full test suite that runs all four modules together automatically, plus a `pyproject.toml` so you can install the tool globally and just type `encrypt` from anywhere instead of the full venv path every time.

Install it globally:
```powershell
venv\Scripts\pip.exe install -e .
```

Run all tests:
```powershell
venv\Scripts\python.exe -m pytest tests/
```
