import requests

test_url = "https://news.google.com/rss/articles/CBMipAFBVV95cUxQVlQ2ZVViQm5UV2d0OWZkV0UwNnZjRXJXdktkZFVBdGlNOFUybk9acmxUQWFCR0dJN3l1dHRTb2YtTUlsaFJQZ0Zfb1d6TzJiVlRVWlliaFI4Y0RvMzBKblh4OXVjQlRLakMtMGd6cVpmTjBNOUFPMUZaQ0pVWnRkUmgxX2NrMFhHMWJxNEw4VlFYZU9YVEdfWjNqTXRBX3ZiS3NTYw?oc=5"

print("Testing URL resolution...")
print(f"Original URL: {test_url}")

# Method 1: HEAD request to check redirects
try:
    response = requests.head(test_url, allow_redirects=True, timeout=20)
    print(f"\nHEAD request final URL: {response.url}")
    print(f"Status code: {response.status_code}")
except Exception as e:
    print(f"HEAD request failed: {e}")

# Method 2: GET request to check redirects
try:
    response = requests.get(test_url, allow_redirects=True, timeout=20)
    print(f"\nGET request final URL: {response.url}")
    print(f"Status code: {response.status_code}")
    print(f"History: {[r.url for r in response.history]}")
except Exception as e:
    print(f"GET request failed: {e}")
