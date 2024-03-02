import requests
import polars as pl
import os

pat = os.environ["TOKEN"]
if not pat:
  raise RuntimeError("TOKEN env var is not set")
headers = {"Authorization": f"token {pat}",
           "Accept": "application/vnd.github.v3+json",
           }

headers = {"Authorization": f"token {pat}",
           "Accept": "application/vnd.github.v3+json",
           }

def get_all_pages(url, params=None):
  all_data = []
  while True:
    response = requests.get(url, params=params, headers = headers)
    if response.status_code == 200:
      data = response.json()
      all_data.extend(data)
      next_link = response.links.get("next", {}).get("url")
      if not next_link:
        break
      url = next_link
    else:
      print(f"Error retrieving releases: {response.status_code}")
      return None
  return all_data

def get_release_versions(username, repo_name, per_page=100):

  url = f"https://api.github.com/repos/{username}/{repo_name}/releases"
  params = {"per_page": per_page}  # Adjust per_page as needed

  all_releases = get_all_pages(url, params)
  if all_releases:
    return [release["tag_name"] for release in all_releases]
  else:
    return None


def get_latest_release_version(username, repo_name):
  url = f"https://api.github.com/repos/{username}/{repo_name}/releases/latest"
  response = requests.get(url, headers=headers)

  if response.status_code == 200:
    data = response.json()
    return data["tag_name"]
  else:
    print(f"Error retrieving releases: {response.status_code}")
    return None


def versions(username, reponame):
    latest_version, early_lat_ver, early_versions = None, None, None
    latest_version = get_latest_release_version(username, reponame)
    versions = get_release_versions(username, reponame)
    
    print(latest_version)
    print(versions)

    if versions!= None:
        early_versions = "absent" if versions[0] == latest_version else "present"
        early_lat_ver = versions[0]
    return latest_version, early_lat_ver, early_versions



df = pl.read_csv("GitHub_Release.csv")
df_new = df.filter(pl.col('version_pattern_match') == 'PatternMatchOnlyNum')

github_latest_vers = []
update_requires = []

for row in df_new.rows():
    username, reponame, winget_latest_ver = row[0], row[1], row[2]

    github_latest_ver, ear_lat_version, early_versions = versions(username, reponame)
    
    if ear_lat_version!= None:
        if winget_latest_ver.lower() in ear_lat_version.lower():
            update_require = "No"
        elif github_latest_ver!= None:
            if winget_latest_ver.lower() in github_latest_ver.lower():
                update_require = "No"
            else:
                update_require = "Yes"
    else:
        update_require = "NA"
        
    print(username)
    print(reponame)
    print(github_latest_ver)
    print(winget_latest_ver)
    print(update_require)
    print()
    
    github_latest_vers.append(github_latest_ver)
    update_requires.append(update_require)
    
df_new = df_new.with_columns([
    pl.Series(name="update_requires", values=update_requires),
    pl.Series(name="github_latest_vers", values=github_latest_vers),
])      
    
df_new.write_csv("GitHub_Releasess.csv")    
