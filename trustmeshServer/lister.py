import os

output_filename = "combined_output.txt"
def listall():
    system = os.walk(top=".")
    filepaths = []
    for root, dirname, filename in system:
        for file in filename:
            if filename == "trustmesh.json":
                continue
            filepaths.append(os.path.normpath(os.path.join(root, file)))
    return filepaths
all_files = listall()

with open(output_filename, 'w', encoding='utf-8') as ouput_file:
    for filename in all_files:
        ouput_file.write(f"// {filename}\n")
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            ouput_file.write(f.read()+"\n")