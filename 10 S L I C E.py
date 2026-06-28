import os
import math

def run_slicer():
    print("--- S L I C E ---")
    filename = input("Filename: ")
    
    if not os.path.exists(filename):
        print(f"\n" + "="*40)
        print(f"'{filename}' not found in the current directory")
        print("-"*40)
        return

    try:
        num_slices = int(input("Slices: "))
        if num_slices <= 0:
            raise ValueError
    except ValueError:
        print("\n"+"="*40)
        print("Slices must be a positive integer")
        print("\n"+"-"*40)
        return

    print("\n"+"="*40)

    file_size = os.path.getsize(filename)
    slice_size = math.ceil(file_size / num_slices)
    
    buffer_size = 1024 * 1024  
    
    with open(filename, 'rb') as infile:
        for i in range(1, num_slices + 1):
            out_filename = f"{i:02d}_{num_slices}_{filename}"
            
            bytes_written = 0
            with open(out_filename, 'wb') as outfile:
                while bytes_written < slice_size:
                    read_size = min(buffer_size, slice_size - bytes_written)
                    chunk = infile.read(read_size)
                    
                    if not chunk:
                        break
                        
                    outfile.write(chunk)
                    bytes_written += len(chunk)
            
            print(f"Saved as {i:02d}_{num_slices:02d}_{filename}")
            
            if not chunk:
                break
                
        print("-"*40)

if __name__ == "__main__":
    run_slicer()
