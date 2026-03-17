"""
Test googlenewsdecoder with Google News URLs
"""
from googlenewsdecoder import new_decoderv1

# Test URL
test_url = "https://news.google.com/rss/articles/CBMic0FVX3lxTFBuRXI4UGlkQWFTV1ViUWxUUWRjbWFoV2MxNG1zZ2NnVTF6dEkwMnA1SzJRU051ZEhEVnR5clBkM21Sbi00MDNISlNwV0tBVHVuQXk4VkRvWmQzU1ZUUkVvQkZWQkt3bVJiVEtTaTlmU2F0WW8?oc=5"

print("Testing googlenewsdecoder...")
print(f"Original URL: {test_url}\n")

try:
    decoded_url = new_decoderv1(test_url, interval=1)
    print(f"Decoded URL: {decoded_url}")

    if decoded_url and decoded_url != test_url:
        print("\n✓ Successfully decoded!")
    else:
        print("\n✗ Decoding failed or returned same URL")

except Exception as e:
    print(f"\n✗ Error: {e}")
