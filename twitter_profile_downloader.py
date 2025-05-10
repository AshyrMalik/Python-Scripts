import os
import re
import requests
import json
import time
from PIL import Image, ImageDraw
import argparse
from urllib.parse import urlparse
from io import BytesIO


def extract_username(text):
    """Extract the username from a Twitter/X URL or @username format."""
    # Check if it's a URL
    if "twitter.com/" in text or "x.com/" in text:
        # Extract username from URL
        parsed = urlparse(text)
        path_parts = parsed.path.strip('/').split('/')
        if path_parts:
            return path_parts[0]
    # Check if it's in @username format
    elif text.startswith('@'):
        return text[1:]
    # Already a username
    else:
        return text


def download_profile_image(username):
    """Download profile image for a given username."""
    try:
        # Twitter now requires a different approach
        # We'll try a direct access to the profile image URL
        # This is more reliable than scraping the HTML

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/jpeg,image/png,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': f'https://twitter.com/{username}'
        }

        # First try the "syndication" API which doesn't require authentication
        syn_url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
        response = requests.get(syn_url, headers=headers)

        if response.status_code == 200:
            content = response.text
            # Look for profile image URL pattern
            profile_image_pattern = r"https://pbs.twimg.com/profile_images/[^\"'\s]+"
            match = re.search(profile_image_pattern, content)

            if match:
                image_url = match.group(0)
                # Replace _normal with _400x400 for higher resolution
                image_url = image_url.replace("_normal", "_400x400")

                # Download the image
                img_response = requests.get(image_url, headers=headers)
                if img_response.status_code == 200:
                    print(f"Successfully found image via syndication API for @{username}")
                    return img_response.content

        # If that fails, try direct URL construction
        # This works because Twitter profile images follow a predictable pattern
        print(f"Trying alternate method for @{username}...")

        # Try to access their API endpoint directly
        api_url = f"https://api.twitter.com/1.1/users/show.json?screen_name={username}"
        response = requests.get(api_url, headers=headers)

        if response.status_code == 200 and 'profile_image_url_https' in response.text:
            data = response.json()
            image_url = data.get('profile_image_url_https', '').replace('_normal', '_400x400')
            if image_url:
                img_response = requests.get(image_url, headers=headers)
                if img_response.status_code == 200:
                    return img_response.content

        # Last resort: Try with nitter.net (a Twitter alternative frontend)
        print(f"Trying nitter.net for @{username}...")
        nitter_url = f"https://nitter.net/{username}/pic"
        response = requests.get(nitter_url, headers=headers, allow_redirects=True)

        if response.status_code == 200:
            return response.content

        print(f"Could not download profile image for @{username}")
        return None
    except Exception as e:
        print(f"Error downloading profile image for @{username}: {e}")
        return None


def make_rounded_image(image_data, output_path):
    """Convert image to rounded shape with transparency."""
    try:
        # Open the image from bytes
        try:
            image = Image.open(requests.io.BytesIO(image_data))
        except:
            # If that fails, try direct file handling
            with open("temp_image", "wb") as f:
                f.write(image_data)
            image = Image.open("temp_image")

        # Convert to RGBA if it's not already
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

        # Create a circular mask
        mask = Image.new('L', image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, image.size[0], image.size[1]), fill=255)

        # Apply the mask to the image
        result = Image.new('RGBA', image.size, (0, 0, 0, 0))
        result.paste(image, (0, 0), mask)

        # Save the result
        result.save(output_path, 'PNG')

        # Clean up temp file if it exists
        if os.path.exists("temp_image"):
            os.remove("temp_image")

        return True
    except Exception as e:
        print(f"Error processing image: {e}")
        return False


def process_usernames(input_file, output_dir):
    """Process each username in the input file."""
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Read usernames from file
    with open(input_file, 'r') as file:
        usernames = [line.strip() for line in file if line.strip()]

    successful = 0
    failed = 0

    # Process each username
    for username in usernames:
        try:
            clean_username = extract_username(username)
            print(f"Processing @{clean_username}...")

            # Try using a direct method to get profile image
            # Twitter profile pictures have a predictable URL pattern
            # Try constructing the URL directly
            direct_url = f"https://unavatar.io/twitter/{clean_username}"
            print(f"Trying direct URL method for @{clean_username}...")

            try:
                # Try to download with unavatar.io service
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                img_response = requests.get(direct_url, headers=headers, timeout=10)

                if img_response.status_code == 200 and len(img_response.content) > 1000:
                    image_data = img_response.content
                    print(f"✅ Got image using unavatar.io for @{clean_username}")
                else:
                    # If that fails, try the more complex method
                    print(f"Unavatar method failed, trying backup method...")
                    image_data = download_profile_image(clean_username)
            except:
                # If direct method fails, try the more complex method
                print(f"Direct method failed, trying backup method...")
                image_data = download_profile_image(clean_username)

            if image_data:
                # Save as rounded PNG
                output_path = os.path.join(output_dir, f"{clean_username}.png")
                if make_rounded_image(image_data, output_path):
                    print(f"✅ Successfully saved {output_path}")
                    successful += 1
                else:
                    print(f"❌ Failed to process image for @{clean_username}")
                    failed += 1
            else:
                print(f"❌ Failed to download image for @{clean_username}")
                failed += 1

            # Add a small delay to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error processing @{clean_username}: {e}")
            failed += 1

    print(f"\nProcessing complete. {successful} successful, {failed} failed.")


def main():
    parser = argparse.ArgumentParser(description='Download Twitter profile images and convert to rounded PNGs')
    parser.add_argument('--input', '-i', required=True, help='Input file containing Twitter usernames')
    parser.add_argument('--output', '-o', default='profile_images', help='Output directory for profile images')

    args = parser.parse_args()

    print("Twitter Profile Image Downloader and Processor")
    print("=" * 50)
    print(f"Input file: {args.input}")
    print(f"Output directory: {args.output}")
    print("=" * 50)

    process_usernames(args.input, args.output)


if __name__ == "__main__":
    main()