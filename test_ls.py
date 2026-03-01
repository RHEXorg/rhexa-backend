import requests

api_key = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiI5NGQ1OWNlZi1kYmI4LTRlYTUtYjE3OC1kMjU0MGZjZDY5MTkiLCJqdGkiOiI0M2Q4Y2Y0MDkwYzQ0NjA1YThiYzgzZDY0NGM2YmRiNDRkMmNlY2I5ZTViZGM2NDA2MjNkOWE0NTZhNzAzMTFlMDk3N2RmMmFiYTc2OTYyZCIsImlhdCI6MTc3MjM1ODIxMC42NDMzNTIsIm5iZiI6MTc3MjM1ODIxMC42NDMzNTUsImV4cCI6MTc4ODIyMDgwMC4wMTk4NzEsInN1YiI6IjY0MDU4NDMiLCJzY29wZXMiOltdfQ.m2rOZlHEh7GUZ0rrB0dO1L06eEGF19lubUWNzPFL3q-B1Y7Fi3eMQ-OcYmExbHU52qR5ChCBHeZ11aOB8ZSBq5Cint2OZQwg6Phim4fs4icKsR4EAPU8F9pJtcuUEdVmOOvt5WEXgBBjYL4vUjpV48iuHoVDsm5SfaFL4XfLFjjTxuugcxunsl1doDlo0tkyb3mQ0a5DjWkT3B8B5UC1ZbDbbBTeHPgrtCXxHKDbwwYJ7HAMn1Ply7mDL1Ry-g4WMN0KJVit4EAzNWQElDGmm0sewHuimgAvRZ1ELFFH7-ouIpEspzpajcDSf0jO3pe_SGz5rfB4CfipKwCOVlgpmOe5Xb9rAlTpSLEAANvkz9gss_n-j7Ryiny3xp0pBXLUZsIu-8pfxvt60ytzFUOaBAFbkgmdWFxx2yB2oYczVLKMMQLJCNdggWhsVTxlDV5A9P4ejPa4IXeN899z4-xzejHhQxIUweMPNHT4kZ-Fyn4psVjZHJdT2CXCUvBS0zOhl7liJ_eNj4XoaxEs8fABlVskhTVenSLIfPOheg0iprwPOToX2y_6UXs0ZHn5YlREUbASXqCbgYlza8BVg-VhtR0jZZZF23tH8_tVieSRhkaA06obfpic_5dbWY5G6BDK21W_NHTXQ5YiaXjq8DHWnV0rdKUe9fWQP0MeBR-GXxs"
headers = {
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/vnd.api+json",
    "Authorization": f"Bearer {api_key}"
}
r = requests.get("https://api.lemonsqueezy.com/v1/variants", headers=headers)
data = r.json()
for variant in data.get('data', []):
    print("Variant ID:", variant['id'])
    print("Name:", variant['attributes']['name'])
    print("Product ID:", variant['attributes']['product_id'])
    print("Price:", variant['attributes']['price'])
    print("---")
