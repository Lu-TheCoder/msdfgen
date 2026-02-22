import os
import sys
import glob
import json
import math
import argparse
import subprocess
from PIL import Image

def find_msdfgen():
    """Finds the msdfgen executable in the standard build directory or PATH."""
    path_in_build = os.path.join(os.path.dirname(__file__), "build", "msdfgen")
    if os.path.exists(path_in_build):
        return path_in_build
    if os.name == 'nt' and os.path.exists(path_in_build + ".exe"):
        return path_in_build + ".exe"
    import shutil
    if shutil.which("msdfgen"):
         return "msdfgen"
    return None

def pack_images(images, padding):
    """
    Packs a list of PIL Images into a single atlas image using a simple grid or skyline approach.
    Returns (atlas_image, list_of_positions_x_y)
    """
    if not images:
        return Image.new("RGBA", (1, 1), (0,0,0,0)), []

    # Sort images by height descending
    sorted_indices = sorted(range(len(images)), key=lambda i: images[i].height, reverse=True)
    
    # Calculate a rough square size for the atlas
    total_area = sum((img.width + padding) * (img.height + padding) for img in images)
    atlas_width = int(math.ceil(math.sqrt(total_area)))
    
    # Make width a power of 2 for better GPU compatibility typically
    atlas_width = 1 << (atlas_width - 1).bit_length()
    
    positions = [None] * len(images)
    
    # Simple shelf packer
    current_x = padding
    current_y = padding
    row_height = 0
    
    for idx in sorted_indices:
        img = images[idx]
        if current_x + img.width + padding > atlas_width:
            current_x = padding
            current_y += row_height + padding
            row_height = 0
        
        positions[idx] = (current_x, current_y)
        row_height = max(row_height, img.height)
        current_x += img.width + padding
        
    atlas_height = current_y + row_height + padding
    
    # Make width and height the same (largest of the two)
    # And round up to the next power of two to guarantee an NxN sheet
    max_dim = max(atlas_width, atlas_height)
    final_size = 1 << (max_dim - 1).bit_length()
    
    atlas = Image.new("RGBA", (final_size, final_size), (0,0,0,0))
    for idx, img in enumerate(images):
        x, y = positions[idx]
        atlas.paste(img, (x, y))
        
    return atlas, positions

def main():
    parser = argparse.ArgumentParser(description="Generate MSDF Atlas from a folder of SVGs")
    parser.add_argument("--input-dir", required=True, help="Directory containing SVG icons")
    parser.add_argument("--output-atlas", default="atlas.png", help="Output PNG file for the atlas")
    parser.add_argument("--output-json", default="atlas.json", help="Output JSON map file")
    parser.add_argument("--size", type=int, default=64, help="Resolution size for each icon's MSDF")
    parser.add_argument("--padding", type=int, default=2, help="Padding pixels between icons in the atlas")
    parser.add_argument("--msdfgen-path", default=None, help="Explicit path to msdfgen binary")
    args = parser.parse_args()

    input_dir = args.input_dir
    if not os.path.exists(input_dir):
        print(f"Error: Directory '{input_dir}' not found.", file=sys.stderr)
        return 1
        
    msdfgen = args.msdfgen_path or find_msdfgen()
    if not msdfgen:
        print("Error: Could not find 'msdfgen' executable. Try specifying --msdfgen-path.", file=sys.stderr)
        return 1

    svg_files = glob.glob(os.path.join(input_dir, "*.svg"))
    if not svg_files:
        print(f"No SVG files found in '{input_dir}'.")
        return 0
        
    print(f"Found {len(svg_files)} SVGs. Generating individual MSDFs...")
    
    # Temp folder for the msdf instances
    temp_dir = os.path.join(input_dir, "_temp_msdf")
    os.makedirs(temp_dir, exist_ok=True)
    
    icons_data = []
    images = []

    for svg in svg_files:
        basename = os.path.basename(svg)
        name, _ = os.path.splitext(basename)
        out_png = os.path.join(temp_dir, f"{name}.png")
        
        # Call MSDFGen:
        # Note: using -autoframe to center the trace within the defined box 
        cmd = [msdfgen, "msdf", "-svg", svg, "-o", out_png, "-size", str(args.size), str(args.size), "-autoframe"]
        
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            img = Image.open(out_png).convert("RGBA")
            images.append(img)
            icons_data.append({"name": name, "file": basename})
            print(f" -> Processed {basename}")
        except subprocess.CalledProcessError as e:
            print(f"Warning: msdfgen failed on '{basename}': {e}", file=sys.stderr)

    if not images:
        print("No images were successfully generated.")
        return 1

    print("Packing images into an atlas...")
    atlas_img, pos_map = pack_images(images, args.padding)
    
    atlas_img.save(args.output_atlas)
    print(f"Saved atlas image to {args.output_atlas} ({atlas_img.width}x{atlas_img.height})")
    
    # Build JSON output
    json_data = {
        "atlas_width": atlas_img.width,
        "atlas_height": atlas_img.height,
        "icons": {}
    }
    
    for i, meta in enumerate(icons_data):
        x, y = pos_map[i]
        w, h = images[i].width, images[i].height
        json_data["icons"][meta["name"]] = {
            "x": x,
            "y": y,
            "width": w,
            "height": h
        }
        
    with open(args.output_json, "w") as f:
        json.dump(json_data, f, indent=4)
    print(f"Saved atlas metadata to {args.output_json}")
    
    # Cleanup temp dir
    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)
    print("Cleanup complete.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
