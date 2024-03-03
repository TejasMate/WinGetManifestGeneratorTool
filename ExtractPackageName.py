import subprocess
import os
import concurrent.futures
import polars as pl
import csv

def run_command(command, cwd=None):
    print(f"Executing command: {command}")
    try:
        result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=cwd)
        print(result.stdout)
        print(result.stderr)
        return result.returncode
    except FileNotFoundError as e:
        print(f"Error executing command: {e}")
        return 1
    
def get_yaml_files_from_local_directory(directory_path=''):
    filenames = set()
    for root, _, files in os.walk(directory_path):
        for filename in files:
            if filename.endswith('.installer.yaml'):
                filenames.add(os.path.join(root, filename))
    return filenames

def process_yaml_file(filename, max_dots, unique_rows):
    name = os.path.basename(filename).replace('.installer.yaml', '')
    parts = name.split('.')
    if len(set(parts)) == 1:
        return
    row = tuple(parts[:max_dots + 1])  # Convert row to a tuple for hashing
    unique_rows.add(row)

if __name__ == '__main__':
    forked_repo = "tejasmate/winget-pkgs"
    upstream_repo = "microsoft/winget-pkgs"
    local_repo = "winget-pkgs"
    
    run_command(f'gh repo sync {forked_repo} --source {upstream_repo}')
    
    if not os.path.exists(local_repo) or not os.path.isdir(local_repo):
        run_command(f'gh repo clone {forked_repo}')
    else:
        run_command(f"cd {local_repo} && gh repo sync --source {forked_repo}")

    manifests_dir_path = f'{local_repo}/manifests/'
    
    yaml_files = get_yaml_files_from_local_directory(manifests_dir_path)
    
    max_dots = 0
    unique_rows = set()  # Store unique rows in a set
    for filename in yaml_files:
        name = os.path.basename(filename).replace('.installer.yaml', '')
        num_dots = name.count('.')
        max_dots = max(max_dots, num_dots)
        
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_yaml_file, filename, max_dots, unique_rows) for filename in yaml_files]
        
        # Wait for all tasks to complete
        concurrent.futures.wait(futures)
        
    with open('filenames.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Generate header row
        header = ['column' + str(i + 1) for i in range(max_dots + 1)]
        writer.writerow(header)
        
        # Use concurrent.futures to process files in parallel
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(process_yaml_file, filename, max_dots, unique_rows) for filename in yaml_files]
            
            # Wait for all tasks to complete
            concurrent.futures.wait(futures)
        
        # Write unique rows to the CSV file
        for row in unique_rows:
            writer.writerow(row)

    column_names = [f"column_{i}" for i in range(max_dots+1)]
    unique_rows = [list(t) + [None] * (max_dots + 1 - len(t)) for t in unique_rows]

    if unique_rows:
        df = pl.DataFrame(unique_rows).transpose().sort(column_names)
        
    
    print("all success")


