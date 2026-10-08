"""Generate a PBKDF2 hash for APP_USERS_JSON without exposing the password."""
import getpass
import hashlib
import secrets

if __name__ == '__main__':
    password = getpass.getpass('Password (12+ characters): ')
    if len(password) < 12:
        raise SystemExit('Use at least 12 characters.')
    if password != getpass.getpass('Confirm password: '):
        raise SystemExit('Passwords do not match.')
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 600000).hex()
    print(f'pbkdf2_sha256$600000${salt.hex()}${digest}')
