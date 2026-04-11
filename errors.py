import sys
import os
from cryptography.exceptions import InvalidTag

ERR_WRONG_PASSWORD  = 1
ERR_BAD_FILE        = 2
ERR_FILE_NOT_FOUND  = 3
ERR_FILE_TOO_SMALL  = 4
ERR_PERMISSION      = 5
ERR_DISK_FULL       = 6
ERR_UNKNOWN         = 99

MESSAGES = {
    ERR_WRONG_PASSWORD : "Wrong password, or the file has been tampered with. Nothing was written.",
    ERR_BAD_FILE       : "This doesn't look like a valid .enc file. Did you pick the right file?",
    ERR_FILE_NOT_FOUND : "Can't find that file. Double-check the path and try again.",
    ERR_FILE_TOO_SMALL : "The file is too small to be a valid encrypted file. It might be corrupted.",
    ERR_PERMISSION     : "Permission denied. You might not have access to read or write that location.",
    ERR_DISK_FULL      : "Ran out of disk space while writing the output file.",
    ERR_UNKNOWN        : "Something unexpected went wrong.",
}

def fail(code, detail=""):
    message = MESSAGES.get(code, MESSAGES[ERR_UNKNOWN])
    if detail:
        print(f"\n  ERROR: {message}\n  Detail: {detail}\n")
    else:
        print(f"\n  ERROR: {message}\n")
    sys.exit(code)

def clean_up(path):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass

def safe_encrypt(encrypt_fn, input_path, output_path, password):
    try:
        encrypt_fn(input_path, output_path, password)
    except FileNotFoundError:
        clean_up(output_path)
        fail(ERR_FILE_NOT_FOUND)
    except PermissionError:
        clean_up(output_path)
        fail(ERR_PERMISSION)
    except OSError as e:
        clean_up(output_path)
        if "No space left" in str(e) or e.errno == 28:
            fail(ERR_DISK_FULL)
        fail(ERR_UNKNOWN, str(e))
    except Exception as e:
        clean_up(output_path)
        fail(ERR_UNKNOWN, str(e))

def safe_decrypt(decrypt_fn, input_path, output_path, password):
    try:
        decrypt_fn(input_path, output_path, password)
    except InvalidTag:
        clean_up(output_path)
        fail(ERR_WRONG_PASSWORD)
    except ValueError as e:
        clean_up(output_path)
        msg = str(e).lower()
        if "too small" in msg or "too short" in msg:
            fail(ERR_FILE_TOO_SMALL)
        if "magic" in msg or "valid" in msg or "version" in msg:
            fail(ERR_BAD_FILE, str(e))
        fail(ERR_UNKNOWN, str(e))
    except FileNotFoundError:
        clean_up(output_path)
        fail(ERR_FILE_NOT_FOUND)
    except PermissionError:
        clean_up(output_path)
        fail(ERR_PERMISSION)
    except OSError as e:
        clean_up(output_path)
        if "No space left" in str(e) or e.errno == 28:
            fail(ERR_DISK_FULL)
        fail(ERR_UNKNOWN, str(e))
    except Exception as e:
        clean_up(output_path)
        fail(ERR_UNKNOWN, str(e))
