import os
from PIL import Image

# Set your source directory where images are stored
source_dir = "./assets/raw"  # Update this to your directory
# Define the output directory (subdirectory)
output_dir = "./assets/partners_and_supporters"

# Create the output directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Define the target resolution
target_width, target_height = 240, 100
target_size = (target_width, target_height)

# List of image file extensions to process
extensions = (".png", ".jpg", ".jpeg", ".bmp", ".gif")

# Set the appropriate resampling filter for Pillow
try:
    # Pillow 10.0 and newer
    resample_filter = Image.Resampling.LANCZOS
except AttributeError:
    # Older versions of Pillow
    resample_filter = Image.LANCZOS

# Process each file in the directory
for filename in os.listdir(source_dir):
    if filename.lower().endswith(extensions):
        file_path = os.path.join(source_dir, filename)
        try:
            with Image.open(file_path) as im:
                # If image is in palette mode or already has an alpha channel and
                # has transparency info, convert using RGBA and composite on white
                if (im.mode == "P" and "transparency" in im.info) or im.mode == "RGBA":
                    im = im.convert("RGBA")
                    # Create a white background (with full opacity)
                    white_bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
                    # Composite the image over white to remove transparency
                    im = Image.alpha_composite(white_bg, im)
                    # Convert back to RGB for further processing
                    im = im.convert("RGB")
                else:
                    im = im.convert("RGB")

                original_width, original_height = im.size

                # Calculate scaling factor while preserving aspect ratio
                scale_factor = min(target_width / original_width, target_height / original_height)
                new_width = int(original_width * scale_factor)
                new_height = int(original_height * scale_factor)

                # Resize the image using the defined resampling filter
                resized_im = im.resize((new_width, new_height), resample_filter)

                # Create a new white background image with target dimensions
                canvas = Image.new("RGB", target_size, (255, 255, 255))

                # Center the resized image on the white canvas
                paste_x = (target_width - new_width) // 2
                paste_y = (target_height - new_height) // 2
                canvas.paste(resized_im, (paste_x, paste_y))

                # Save the final image in the output directory
                output_path = os.path.join(output_dir, filename)
                canvas.save(output_path)
                print(f"Processed and saved: {output_path}")

        except Exception as e:
            print(f"Error processing {filename}: {e}")
