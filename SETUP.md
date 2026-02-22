# Setting up MSDFGen

This guide walks you through compiling the `msdfgen` project from source and generating SVG assets.

## Building from Source

To ensure that the SVG importer correctly builds paths with stroke attributes (e.g. `fill="none"` and `stroke-width="..."`), the engine must be built with `Skia` enabled (`MSDFGEN_USE_SKIA=ON`).
This requires `vcpkg` to be installed and available on your system path.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Chlumsky/msdfgen.git
   cd msdfgen
   ```
2. **Configure the build with CMake:**
   ```bash
   mkdir build && cd build
   cmake .. -DMSDFGEN_BUILD_STANDALONE=ON -DMSDFGEN_USE_SKIA=ON
   ```
3. **Compile the binary:**
   ```bash
   cmake --build . --config Release
   ```

## Generating a Single MSDF
Once you've built the executable, you can generate a Multichannel Signed Distance Field for a single SVG file:
```bash
./msdfgen msdf -svg home.svg -size 1024 1024 -autoframe -o icon.png
```

## Generating a Sprite Atlas

To generate a uniform square atlas from a folder of SVG icons (perfect for game engines), you can use the included Python script. This will use Pillow to pack MSDF textures side-by-side and output the mapping coordinates to a JSON file.

### Prerequisites
You'll need the Pillow package to stitch the images together:
```bash
pip install Pillow
```

### Usage
```bash
python3 generate_atlas.py --input-dir build/icons --output-atlas atlas.png --output-json atlas.json --size 64
```

### Arguments
- `--input-dir`: Directory containing `.svg` files (e.g., `build/icons`).
- `--output-atlas`: The desired output image name (default: `atlas.png`).
- `--output-json`: The desired output coordinate map (default: `atlas.json`).
- `--size`: The MSDF distance field resolution squared size for each icon inside the atlas (default: `64`).
- `--padding`: The number of empty pixels serving as a border separator between packed icons (default: `2`).
