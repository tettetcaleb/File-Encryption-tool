# File Encryption Tool

I built this because I wanted a simple way to encrypt any file with a password — no apps, no accounts, just a command and a password and your file is locked. It uses AES-256, which is the same encryption standard used by banks and governments, so it's not a toy.

The whole thing is written in Python and runs from the terminal.

---

## What it can do

- Encrypt any file — PDFs, images, videos, zip files, whatever
- Decrypt it back with the same password
- Reject wrong passwords immediately with a clean error message
- Detect if a file has been tampered with
- Handle every failure gracefully — no Python tracebacks, just plain English errors

---

## How to install the one dependency

```powershell
venv\Scripts\pip.exe install cryptography
```

That's the only external package. Everything else is standard Python.

---

## How to use it

**Encrypt a file:**
```powershell
venv\Scripts\python.exe encrypt_tool.py --encrypt --input myfile.pdf --output myfile.enc
```

**Decrypt a file:**
```powershell
venv\Scripts\python.exe encrypt_tool.py --decrypt --input myfile.enc --output myfile.pdf
```

It'll ask for your password when you run it. Nothing shows on screen while you type — that's normal.

When encrypting it asks you to confirm the password so you don't lock yourself out with a typo.

---

## Important — always use the venv Python

Never use the VS Code play button or just type `python`. Always use `venv\Scripts\python.exe` in the terminal. The play button points to the system Python which doesn't have the `cryptography` package.

---

## How the project is structured

I split everything into four files so each one does exactly one job.

```
Fle_encryption\
├── crypto_engine.py    ← the raw AES-256 math
├── file_format.py      ← adds a header to encrypted files so we can identify them
├── errors.py           ← catches every failure and explains it in plain English
├── encrypt_tool.py     ← the CLI you actually type into
└── venv\               ← virtual environment (cryptography lives here)
```

---

## Step 1 — The core encryption engine (`crypto_engine.py`)

This is where the actual cryptography happens. No CLI, no file format, no UI — just the function that takes bytes in and spits encrypted bytes out.

**Why AES-256-GCM?**

AES-256 is the standard. The GCM part means the encryption is authenticated — decryption doesn't just decrypt, it also checks that the file hasn't been changed since it was encrypted. If someone flips a single bit in your file, or you type the wrong password, you get an error immediately instead of garbage output.

**Why PBKDF2 with 600,000 iterations?**

Your password is something a human can remember, which means it's too short to use directly as a crypto key. PBKDF2 runs your password through SHA-256 hashing 600,000 times to stretch it into a proper key. A correct password derives the key in under a second. An attacker brute-forcing it has to do 600,000× more work per guess. This number is from NIST's 2023 recommendation.

**Why a random salt?**

16 random bytes generated fresh every time you encrypt something. It means two files encrypted with the same password get completely different keys, so an attacker can't attack both at once. The salt isn't secret — it's stored at the start of the output.

**Why a random IV?**

Without a random IV, encrypting the same file twice with the same password would produce identical output, which leaks information. The IV (12 bytes, the recommended GCM size) makes every encryption unique. Also stored in the output, also not secret.

**What the output looks like:**

```
[ 16 bytes ] salt        — mixed into key derivation
[ 12 bytes ] IV          — makes each encryption unique
[ N+16 bytes] ciphertext — your data + 16-byte GCM auth tag

Total overhead: 44 bytes per file
```

**Run the self-test:**

```powershell
venv\Scripts\python.exe crypto_engine.py
```

```
Running crypto_engine self-test...

  Original size :     3300 bytes
  Encrypted size:     3344 bytes  (+44 bytes overhead)
  Decrypt (correct password): PASS
  Decrypt (wrong password)  : PASS — correctly rejected
  Randomness check          : PASS — each encryption is unique

All tests passed.
```

---

## Step 2 — The CLI (`encrypt_tool.py`)

With the crypto working I wrapped it in a proper command-line interface. You pass it flags, it does the work.

**Flags:**

| Flag | What it does |
|---|---|
| `--encrypt` | Encrypt mode |
| `--decrypt` | Decrypt mode |
| `--input FILE` | File to read |
| `--output FILE` | Where to write the result |

**What happens when you encrypt:**

1. You pass `--input` and `--output`
2. It prompts for a password (hidden)
3. It asks you to confirm the password
4. File gets encrypted and saved
5. You see the sizes and time taken

**What happens when you decrypt:**

1. You pass `--input` and `--output`
2. It prompts for the password
3. Correct password → file gets decrypted
4. Wrong password → clean error, no output file left behind

---

## Step 3 — File format (`file_format.py`)

Before this, encrypted output was just a blob of random-looking bytes. There was no way to tell if it was one of our files or random garbage. If you tried to decrypt the wrong file it would crash with a confusing Python error.

So I added a 33-byte header to the start of every `.enc` file that acts like an ID card.

**What's inside every `.enc` file:**

```
[ 4 bytes ] Magic: "AES\x00"  — proves this is our file
[ 1 byte  ] Version: 1        — which version of the format
[ 16 bytes] Salt              — for key derivation
[ 12 bytes] IV                — for encryption
[ the rest] Ciphertext        — your data + 16-byte GCM tag

Total overhead: 49 bytes
```

The magic bytes let the tool immediately tell if you gave it a valid file. If they're not there it says "this isn't a valid .enc file" right away instead of doing work and then crashing.

The version byte means if the format ever changes in the future, old files still say `1` and the tool can handle both without getting confused.

**Run the self-test:**

```powershell
venv\Scripts\python.exe file_format.py
```

```
Running file_format self-test...

  Original size  : 3400 bytes
  Encrypted size : 3449 bytes
  Header overhead: 33 bytes (magic + version + salt + IV)
  GCM tag        : 16 bytes
  Total overhead : 49 bytes

  Magic bytes check : PASS
  Version byte check: PASS
  Roundtrip decrypt : PASS
  Bad magic rejected: PASS

All tests passed.
```

---

## Step 4 — Error handling (`errors.py`)

Before this step, if anything went wrong you'd get a Python traceback like:

```
Traceback (most recent call last):
  File "encrypt_tool.py", line 61, in run_decrypt
cryptography.exceptions.InvalidTag
```

Useless. So I wrote `errors.py` to catch every failure and translate it into plain English.

Now you get this:

```
  ERROR: Wrong password, or the file has been tampered with. Nothing was written.
```

**Every error that's handled:**

- **Wrong password** — told immediately, any partial output file gets deleted automatically
- **File not found** — if you mistyped the path or the file moved
- **Not a valid .enc file** — catches bad magic bytes, explains what happened
- **File too small / corrupted** — detects if the file got cut off or damaged
- **Permission denied** — if you don't have access to that location
- **Disk full** — partial file gets cleaned up automatically

The cleanup part matters. If something goes wrong during decryption, the partial output file gets deleted. You're never left with a half-decrypted file on disk that looks complete but isn't.

**Run the self-test:**

```powershell
venv\Scripts\python.exe errors.py
```

```
Running errors self-test...

  Correct password decrypts successfully : PASS
  Wrong password caught                  : PASS
  Missing file caught                    : PASS
  Bad file format caught                 : PASS

4/4 tests passed.
```

---

## Quick reference

| What I want to do | Command |
|---|---|
| Encrypt a file | `venv\Scripts\python.exe encrypt_tool.py --encrypt --input file.pdf --output file.enc` |
| Decrypt a file | `venv\Scripts\python.exe encrypt_tool.py --decrypt --input file.enc --output file.pdf` |
| Test crypto engine | `venv\Scripts\python.exe crypto_engine.py` |
| Test file format | `venv\Scripts\python.exe file_format.py` |
| Test error handling | `venv\Scripts\python.exe errors.py` |
| Install dependency | `venv\Scripts\pip.exe install cryptography` |

---

## What's coming in Step 5

Step 5 is the finish line — a full test suite that runs all four modules together automatically, plus packaging so you can install the tool globally and just type `encrypt` from anywhere instead of the full `venv\Scripts\python.exe` path every time.
