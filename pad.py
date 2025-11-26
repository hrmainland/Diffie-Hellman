from crypto_utils import *

print(get_rsa_constants().private_numbers().d)
print()
print(get_rsa_constants().public_key().public_numbers().n)
print()
print(get_rsa_constants().public_key().public_numbers().e)
