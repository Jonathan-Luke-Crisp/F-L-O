import os
from PIL import Image

def main():
    print("--- D E R E Z ---")
    input_path = input("Filename: ").strip()
    
    if not os.path.exists(input_path):
        print("\n" + '=' * 30)
        print(f"Can't find {input_path}")
        return

    print("\n" + '=' * 30)
    
    try:
        comp_choice = int(input("Compress: ").strip())
        if not (1 <= comp_choice <= 9):
            raise ValueError("Compression must be between 1 and 9.")
            
        scale_choice = int(input("Scale:    ").strip())
        if not (1 <= scale_choice <= 9):
            raise ValueError("Scale must be between 1 and 9.")
            
        scale_factor = scale_choice / 10.0
        
    except ValueError as e:
        print(f"Invalid input: {e}")
        return

    dir_name, file_name = os.path.split(input_path)
    output_path = os.path.join(dir_name, f"derez_{file_name}")
    is_png = input_path.lower().endswith('.png')

    try:
        with Image.open(input_path) as img:
            new_width = int(img.width * scale_factor)
            new_height = int(img.height * scale_factor)
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            if is_png:
                resized_img = resized_img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
                
                png_compress = 10 - comp_choice
                resized_img.save(output_path, optimize=True, compress_level=png_compress)
            else:
                jpg_quality = comp_choice * 10
                resized_img.save(output_path, optimize=True, quality=jpg_quality)
            
            original_size = os.path.getsize(input_path) / 1024
            new_size = os.path.getsize(output_path) / 1024
            
            print("·" * 30)
            print(f"In:  {original_size:.1f} KB")
            print(f"Out: {new_size:.1f} KB")
            print("-" * 30)
            print(f"Saved as {output_path}")
            print("-" * 30)

    except Exception as e:
        print(f"Error processing image: {e}")

if __name__ == "__main__":
    main()
