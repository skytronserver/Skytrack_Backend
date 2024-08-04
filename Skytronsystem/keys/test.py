from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import base64



private_key_pem=b'''-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDqFQ3sXUsewm7t
8Jgx3ZIE6i3ef75g8DgjX08nFW8+Y1u/ZKabyisKeWnl1o0ArLwe24sddyVKZVJU
voz0nx/YTaZSXTOV+zfgrJzE2zokFXz7oxlKWxbpKW3ApO6FYJwBUDmwr2cvfnwx
yUPApm/dhrhNw1XAPJmWdP9Iwm9HAGL94e1h6niCIoHuaesx4JIvdB1EyhI9f+iF
xAEhGwND+s95vh6l6kcHrLLeJDt336MGXEJK/kqSKC7TuRwIrMM0q2471Zs2SD/j
pxK0YsOaWdJxhRo3tMksGnOoEeSWIyh7EpxiU9Eb/4CmqIagH2HO1vWB/AF1OU5S
Em2c3TJTAgMBAAECggEAEj6Z2zZaSId3BeyesCRI4UEvWgwy1nNirL8c+DrfdMlh
uUUrBzF2sVZNPrC+RLMx5mXOLfm/WlETXa+MZPSSEtXahMjm4GW4MTbC8UT0/yL9
ns9ThUwcOQgVmdJBFPw2rJOIK5FARZ9iJq89LKLMTUPW0ZjL8jPG9MchrpYY/juP
Uc/YYGxsZYOjnYdkuva7dFUjvJZs208xJX1T9S4TVsyet2ffUkznZ7XdsAqx+9Rj
J0FYc1sP4cIrwZN1q71bDSEWJfCR2/4fjTChhfGrM9f+M34wxQ/sJZtcsefclFNJ
rnTE99kP5xUVWGp/hnppLx1cKQKtHPi1Fs7YQ3Gj4QKBgQD4NJCXgNazhnzLyVRQ
kOihQm2+fgrRaxmrHafZsTZrRTSPZNKGZh9RagPAfKAp5uflT3CzpgcP8EsNZ7eI
vcMt0qVLuaqE4nzkIqC0+YiYPW2iQnvRShF5NxxEYzMGQRI0aCUacQeBeELWJY2h
IN81hjwH8dyDD9PEX48GJzQYtwKBgQDxbvKaoHxfpgt+Ww96CNa+Dav0cNZvccU9
X12imbByEARR7BhdAG7buXYoaYP3lEHD8m9H1+jVWpgXz+EjEdPK+/pX4dtPbtvR
3XuBSNNLw2csmd34YHjz3Vyw6NO31SxRNHveuqslVU3I5oz3fYzE9xZA1vJ7aByq
P0vrp66/RQKBgQCuNrcGoDgS6mLN5xJ3Oj8OcUH2YyHUvAfYQ4h9FBXOVVT/ERVz
oFp7Gp5njRIeVySNn6TLc82hMlh7oEECia9limTbMgauHwrqViPW4w8tTHCXY3Ll
A8gf/L6qgbZevW25ux/P32YVSgQfq1wtrJT/TKj2Kp1MoN9TBn+tIfc/IQKBgArw
BMueg6PtqM2joHLd3aSkh+q+BejslYvvOxW3sreoJBn2ATCNaXhI0aKJDTJ1I/mV
jRcLIAAyZ3uErmVhVF/4xGGg2MejdQ/v4b18qB3hj1YE7npnHHOnzqAxHA5S+PwA
za/Mcx5w2+JDF5XKuUrfCsILOtb+Y3YPAgh+AzulAoGBAMOMC2oXVF4kkudI9ikL
tX0ZQBQGBslb2ggNjqVpJr4W9K+zUAzw5Cl5WjQu1tNwSYctv5MusXftjvhk/h8y
5FCcViaiDKLfOYGwyZI8Fzxy4TYCGvpfELY5Zn3aREXHVATcwRbwCD5lVyBRV4Nc
SQzo9knukLgxb34bLXkG0PA9
-----END PRIVATE KEY-----'''


# Public key
public_key_pem = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA6hUN7F1LHsJu7fCYMd2S
BOot3n++YPA4I19PJxVvPmNbv2Smm8orCnlp5daNAKy8HtuLHXclSmVSVL6M9J8f
2E2mUl0zlfs34KycxNs6JBV8+6MZSlsW6SltwKTuhWCcAVA5sK9nL358MclDwKZv
3Ya4TcNVwDyZlnT/SMJvRwBi/eHtYep4giKB7mnrMeCSL3QdRMoSPX/ohcQBIRsD
Q/rPeb4epepHB6yy3iQ7d9+jBlxCSv5Kkigu07kcCKzDNKtuO9WbNkg/46cStGLD
mlnScYUaN7TJLBpzqBHkliMoexKcYlPRG/+ApqiGoB9hztb1gfwBdTlOUhJtnN0y
UwIDAQAB
-----END PUBLIC KEY-----"""

# Load the public key
public_key = RSA.import_key(public_key_pem)

# Encrypt the password
password = "123456789".encode()
cipher = PKCS1_OAEP.new(public_key)
encrypted_password = cipher.encrypt(password)

# Encode the encrypted password in base64
encrypted_password_base64 = base64.b64encode(encrypted_password).decode('utf-8')

print("Encrypted password (base64):", encrypted_password_base64)

private_key_path = '/var/www/html/skytron_backend/Skytronsystem/keys/private_key.pem' #os.getenv('PRIVATE_KEY_PATH', '/var/www/html/skytron_backend/Skytronsystem/keys/private_key.pem')
with open(private_key_path, 'rb') as key_file:
    private_key = RSA.import_key(key_file.read()) 

cipher = PKCS1_OAEP.new(private_key) 
enc=base64.b64decode(encrypted_password_base64)
print(enc)
decrypted_data = cipher.decrypt(enc)
print(decrypted_data)

'''oBl2W1rlX5kZ+eGDjzRO8ClLOIMRIE36suwaeTipFJzQXDsDMH6tA6uJ3SfFTPXdCqYHQDb2VFoYtNMdzoIxTJ6yimHzetInljZUdhQdvfOfa534l02xuevVUwSPka6OvBI7HYaPtfkO7iQ9voUtKpYdV/RUwX8uJld6nuf00d5ekZIG0WbKnNhfUMPj4F8CFoEVrzxGBERT0cBs+gVEPHIk8KlS5rRSreaASBe0IMFq+tCg72r7UOJrTkDidsQbagzEj3JKFBV2abUy2/1cHR2owfBZwXpcZMpY85jFthJJ7FA1LrD3O9NknONaAVRm9RKLOtLdDBg3f3bEjTDuNg=='''