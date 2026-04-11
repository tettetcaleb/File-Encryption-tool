"""
encrypt_tool.py — Command-line interface for AES-256-GCM file encryption
=========================================================================
Wraps crypto_engine.py with a user-friendly CLI.

Usage:
    Encrypt a file:
        venv\Scripts\python.exe encrypt_tool.py --encrypt --input secret.pdf --output secret.pdf.enc

    Decrypt a file:
        venv\Scripts\python.exe encrypt_tool.py --decrypt --input secret.pdf.enc --output secret.pdf

Run with --help to see all options.
"""

import argparse
import getpass
import os
import sys
import time

from crypto_engine import encrypt_file, decrypt_file
from cryptography.exceptions import InvalidTag


#  Helpers 

def get_password_for_encrypt() -> str:
    """Prompt for a password twice and confirm they match."""
    while True:
        password = getpass.getpass("  Enter password    : ")
        if len(password) < 6:
            print("  Password must be at least 6 characters. Try again.\n")
            continue
        confirm = getpass.getpass("  Confirm password  : ")
        if password != confirm:
            print("  Passwords do not match. Try again.\n")
            continue
        return password


def get_password_for_decrypt() -> str:
    """Prompt for a password (no confirmation needed for decrypt)."""
    return getpass.getpass("  Enter password: ")


def file_size_str(path: str) -> str:
    """Return a human-readable file size string."""
    size = os.path.getsize(path)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


#  Main logic 

def run_encrypt(input_path: str, output_path: str) -> None:
    print(f"\n  Encrypting: {input_path}")
    print(f"  Output    : {output_path}\n")

    password = get_password_for_encrypt()

    print("\n  Working...", end="", flush=True)
    start = time.time()
    encrypt_file(input_path, output_path, password)
    elapsed = time.time() - start

    print(f"\r  Done in {elapsed:.2f}s")
    print(f"  Input size : {file_size_str(input_path)}")
    print(f"  Output size: {file_size_str(output_path)}")
    print(f"\n  File encrypted successfully.\n")


def run_decrypt(input_path: str, output_path: str) -> None:
    print(f"\n  Decrypting: {input_path}")
    print(f"  Output    : {output_path}\n")

    password = get_password_for_decrypt()

    print("\n  Working...", end="", flush=True)
    start = time.time()
    try:
        decrypt_file(input_path, output_path, password)
    except InvalidTag:
        print("\r  ERROR: Wrong password or file has been tampered with.\n")
        # Remove incomplete output file if it was created
        if os.path.exists(output_path):
            os.remove(output_path)
        sys.exit(1)
    except ValueError as e:
        print(f"\r  ERROR: {e}\n")
        sys.exit(1)

    elapsed = time.time() - start
    print(f"\r  Done in {elapsed:.2f}s")
    print(f"  Output size: {file_size_str(output_path)}")
    print(f"\n  File decrypted successfully.\n")


#  Argument parsing

def parse_args():
    parser = argparse.ArgumentParser(
        prog="encrypt_tool",
        description="AES-256-GCM file encryption tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  Encrypt a file:
    python encrypt_tool.py --encrypt --input report.pdf --output report.pdf.enc

  Decrypt a file:
    python encrypt_tool.py --decrypt --input report.pdf.enc --output report.pdf
        """
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--encrypt", action="store_true", help="Encrypt a file")
    mode.add_argument("--decrypt", action="store_true", help="Decrypt a file")

    parser.add_argument("--input",  required=True, metavar="FILE", help="Path to the input file")
    parser.add_argument("--output", required=True, metavar="FILE", help="Path to the output file")

    return parser.parse_args()


def main():
    args = parse_args()

    # Validate input file exists
    if not os.path.exists(args.input):
        print(f"\n  ERROR: Input file not found: {args.input}\n")
        sys.exit(1)

    # Warn if output file already exists
    if os.path.exists(args.output):
        answer = input(f"\n  Output file already exists: {args.output}\n  Overwrite? (y/n): ")
        if answer.lower() != "y":
            print("  Cancelled.\n")
            sys.exit(0)

    if args.encrypt:
        run_encrypt(args.input, args.output)
    else:
        run_decrypt(args.input, args.output)


if __name__ == "__main__":
    main()