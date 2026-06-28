import os
import re

def run_stitcher():
    print("--- S T I T C H ---")
    folder = input("Folder: ")
    
    if not os.path.isdir(folder):
        print("\n" +"="*30)
        print(f"Folder '{folder}' not found")
        print("-"*30)
        return

    files = os.listdir(folder)
    slice_pattern = re.compile(r"^(\d+)_(\d+)_(.+)$")
    
    file_jobs = {}
    
    for f in files:
        match = slice_pattern.match(f)
        if match:
            current_idx = int(match.group(1))
            total_count = int(match.group(2))
            orig_filename = match.group(3)
            
            job_key = (orig_filename, total_count)
            if job_key not in file_jobs:
                file_jobs[job_key] = {}
            
            file_jobs[job_key][current_idx] = f

    if not file_jobs:
        print("No valid file slices found in the specified folder")
        return

    print("\n"+"="*30)

    for (orig_filename, total_count), slices in file_jobs.items():
        missing_parts = [i for i in range(1, total_count + 1) if i not in slices]
        
        if missing_parts:
            print(f"Cannot stitch '{orig_filename}'. Missing parts: {missing_parts}")
            continue
            
        output_path = orig_filename
        buffer_size = 1024 * 1024
        
        with open(output_path, 'wb') as outfile:
            for i in range(1, total_count + 1):
                slice_path = os.path.join(folder, slices[i])
                with open(slice_path, 'rb') as infile:
                    while True:
                        chunk = infile.read(buffer_size)
                        if not chunk:
                            break
                        outfile.write(chunk)
                        
        print(f'Saved as "{orig_filename}"')
        print("-"*30)

if __name__ == "__main__":
    run_stitcher()
