import os
import yaml
import json
import csv
import re
import polars as pl

# Define the base directory where the structure starts
base_directory = "winget-pkgs/manifests/"  # Update this path
installer_urls = list()

# Define the schema with four string columns
schema = [
    ("username", str),
    ("reponame", str),
    ("latest_ver", str),
    ("extension", str),
    ("pkgs_name", str),
    ("pkg_pattern", str),
    ("version_pattern_match", str)
]

# Create an empty DataFrame with the specified schema
new_df = pl.DataFrame([], schema=schema)

def version_key(version):
    return [int(x) if x.isdigit() else x for x in re.split(r'([0-9]+)', version)]

def is_dot_number_string(text):
    pattern = r'^[\d.]+$'
    if re.match(pattern, text):
        return True
    else:
        return False

# Read the CSV file with the directory structure
with open("data/filenames.csv", "r", encoding='utf-8') as csv_file:  # Replace with your CSV file path
    csv_reader = csv.reader(csv_file)
    next(csv_reader)  # Skip the header row if it exists

    for row in csv_reader:
                      
        row = [element for element in row if element]

        count = 0
        # Combine elements into a single string with "/" separator
        slashrow = "/".join(row) + "/"
        dotrow = ".".join(row) + "."

        # Construct the directory path based on the pattern
        directory_path = os.path.join(base_directory, f"{slashrow[0].lower()}/{slashrow}")


        subdirectories = [subdir for subdir in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, subdir))]
        file_found = False
        subdirectories.sort(reverse=True)  
        
        # print("-------------------------------")
        # print(directory_path)
        # print(subdirectories)
        # print("-------------------------------")


        
        
        while True:
            #versions = ['2.0.9a', 'f050489', '2.0.15', '2.0.14', '2.0.12', '2.0.11', '2023.07.13']
    
            # Sort the list in descending order
            sorted_versions = sorted(subdirectories, key=version_key, reverse=True)
    
            # Find the first element
            first_element = sorted_versions[0]

            
            subdir_path = os.path.join(directory_path, first_element)
            file_path = os.path.join(subdir_path, f'{dotrow}installer.yaml')
            
                        
            print(sorted_versions)
            print(first_element)
            print(file_path)
            print()
            
            if os.path.exists(file_path):
                # print(f"The first element in descending order is: {first_element}")
                break
            else:
                subdirectories.remove(first_element)
                
                
        with open(file_path, "r", encoding='utf-8') as file:
            if file_path.endswith(".json"):
                data = json.load(file)
            else:
                # print(file)
                data = yaml.safe_load(file)
            
            
            if 'Installers' in data:
              for installer in data['Installers']:
                if 'InstallerUrl' in installer and 'https://github.com' in installer['InstallerUrl']:
                  # print('InstallerUrl found:', installer['InstallerUrl'])
                  count+=1
                  # installer_urls.append(installer['InstallerUrl'])
                  
                  
            if count == 1:
                # print('InstallerUrl found:', installer['InstallerUrl'])
                
                # Split the URL by "/" to get the filename
                parts =  installer['InstallerUrl'].split("/")
                url_ext = parts[-1]
                
                # Split the filename by "." to get the file extension
                extension = url_ext.split(".")[-1]
                
                # Check if the extension is one of the specified values
                allowed_extensions = ["msixbundle", "appxbundle", "msix", "appx", "zip", "msi", "exe"]
                if extension in allowed_extensions:
                    installer_urls.append(installer['InstallerUrl'])
                    # print("Detected extension:", extension)
                    
                    # Define the regular expression pattern to match the username and repository name
                    pattern = r"https://github\.com/([^/]+)/([^/]+)/"

                    # Use re.search() to find the match in the URL
                    match = re.search(pattern, installer['InstallerUrl'])

                    if match:
                        username = match.group(1)
                        repo_name = match.group(2)
                        
                        # print("Username:", username)
                        # print("Repository Name:", repo_name)
                        # print()
                        

                        version_pattern_match = ""

                        if first_element in url_ext:
                            # if first_element.startswith("release-") and is_dot_number_string(first_element[8:]):
                            #     version_pattern_match = "MatchPatternStartWithRelease-"
                            # elif first_element.startswith("RELEASE") and is_dot_number_string(first_element[7:]):
                            #     version_pattern_match = "MatchPatternStartWithRelease"
                            if is_dot_number_string(first_element):
                                version_pattern_match = "PatternMatchOnlyNum"
                            elif first_element.startswith("v") and is_dot_number_string(first_element[1:]):
                                version_pattern_match = "PatternMatchStartWithv"
                            elif first_element.startswith("r") and is_dot_number_string(first_element[1:]):
                                version_pattern_match = "PatternMatchStartWithr"
                            else:
                                version_pattern_match = "PatternMatchExact"
                            # else:
                            #     version_pattern_match = "sameasversionptn"
                        else:
                            if url_ext.count('.')-1 > first_element.count('.'):
                                if "-" in first_element:
                                    string1 = re.sub(r'(\d+(?:\.\d+)*)-', r'\1.0-', first_element)
                                    if string1 in url_ext:
                                        version_pattern_match = "DiffMatchDotZeroIncrease"
                            elif url_ext.count('.')-1 < first_element.count('.'):
                                if "-" in first_element:
                                    pattern = r'(\d+)(?:\.\d+)*(-)'
                                    string1 = re.sub(pattern, lambda x: x.group(1) + ".0" + x.group(2) if "." not in x.group(1) else x.group(0), first_element)

                                    # string1 = re.sub(r'(\d+\.\d+)\.0(?=-)', r'\1', first_element)
                                    if string1 in url_ext:
                                        version_pattern_match = "DiffMatchDotZeroReduce"
                            # elif first_element.startswith("release-") and is_dot_number_string(first_element[8:]):
                            #     version_pattern_match = "NotMatchPatternStartWithRelease-"
                            # elif first_element.startswith("RELEASE") and is_dot_number_string(first_element[7:]):
                            #     version_pattern_match = "NotMatchPatternStartWithRelease"
                            # elif first_element.startswith("v") and is_dot_number_string(first_element[1:]):
                            #     version_pattern_match = "NotMatchPatternStartWithv"
                            # elif first_element.startswith("r") and is_dot_number_string(first_element[1:]):
                            #     version_pattern_match = "NotMatchPatternStartWithr"
                            else:
                                version_pattern_match = "different"


                            
                        df = pl.DataFrame({"username": username, "reponame": repo_name, "latest_ver": first_element, "extension": extension, "pkgs_name": dotrow[:-1], "pkg_pattern": url_ext, "version_pattern_match": version_pattern_match})
                        # new_df = pl.concat([new_df, df], rechunk=True)
                        new_df.extend(df)
                else:
                    print("Extension not in the list of allowed extensions.")
                            
new_df.write_csv("data/GitHub_Release.csv")

with open("data/urls.txt", "w") as file:
    for item in installer_urls:
        file.write(item + "\n")  # Add a newline character to separate elements
        