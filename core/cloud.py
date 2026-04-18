import zipfile
import os
import json
import requests
import ui.splash as splash

AUTH_FILE = ".opendav_auth"

class OpenDAVCloud:
    def __init__(self):
        self.base_url = "" # Set from settings
        self.anon_key = "" # Set from settings
        self.user_id = ""
        self.token = self.load_token()
        self.load_cloud_settings()

    def load_cloud_settings(self):
        from core.config import load_config
        config = load_config()
        self.base_url = config.get("supabase_url", "")
        self.anon_key = config.get("supabase_key", "")

    def load_token(self):
        if os.path.exists(AUTH_FILE):
            with open(AUTH_FILE, 'r') as f:
                data = json.load(f)
                self.user_id = data.get("user", {}).get("id", "")
                return data.get("access_token", "")
        return ""

    def save_token(self, token_data):
        with open(AUTH_FILE, 'w') as f:
            json.dump(token_data, f)
        self.token = token_data.get("access_token", "")
        self.user_id = token_data.get("user", {}).get("id", "")

    def is_logged_in(self):
        return bool(self.token)

    def login(self, email, password):
        if not self.base_url or not self.anon_key:
            print("[!] Supabase settings missing. Configure them in Settings menu.")
            return False

        url = f"{self.base_url}/auth/v1/token?grant_type=password"
        headers = {"apikey": self.anon_key, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}

        try:
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                self.save_token(r.json())
                print(f"[+] Successfully logged in as {email}")
                return True
            else:
                print(f"[!] Login failed: {r.json().get('error_description', 'Unknown error')}")
                return False
        except Exception as e:
            print(f"[!] Network error: {e}")
            return False


    def signup(self, email, password):
        if not self.base_url or not self.anon_key:
            print("[!] Supabase settings missing. Configure them in Settings menu.")
            return False

        url = f"{self.base_url}/auth/v1/signup"
        headers = {"apikey": self.anon_key, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}

        try:
            r = requests.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                print(f"[+] Account created for {email}! You can now login.")
                return True
            else:
                print(f"[!] Signup failed: {r.json().get('msg', r.json().get('error_description', 'Unknown error'))}")
                return False
        except Exception as e:
            print(f"[!] Network error: {e}")
            return False

    def logout(self):
        if os.path.exists(AUTH_FILE):
            os.remove(AUTH_FILE)
        self.token = ""
        print("[+] Logged out from OpenDAV Cloud.")

    def get_headers(self):
        return {
            "apikey": self.anon_key,
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

    def push_project(self, project_name, local_path):
        if not self.is_logged_in():
            print("[!] You must be logged in to push projects.")
            return

        state_file = os.path.join(local_path, "project_state.json")
        if not os.path.exists(state_file):
            print("[!] Project state not found locally.")
            return

        with open(state_file, 'r') as f:
            state = json.load(f)

        print(f"\n[*] Pushing project '{project_name}' to OpenDAV Cloud...")
        
        # 1. Upsert Project Metadata to Database (Table: projects)
        db_url = f"{self.base_url}/rest/v1/projects"
        payload = {
            "name": project_name,
            "state_json": state
        }
        
        try:
            r = requests.post(db_url, headers=self.get_headers(), json=payload)
            # 409 means conflict (already exists), which is fine for a simple implementation, 
            # we should really use UPSERT (Prefer: resolution=merge-duplicates) but Supabase requires a PK.
            # For this CLI, we will just focus on the Storage bucket for now since the DB schema might not be set up by the user yet!
            if r.status_code not in [200, 201, 204, 409]:
                # We won't strictly fail here because the user might not have created the 'projects' table yet.
                pass
        except:
            pass

        # 2. Upload Files to S3 Bucket (Bucket: opendav_assets)
        bucket_url = f"{self.base_url}/storage/v1/object/opendav_assets"
        
        # Collect files to upload
        upload_queue = []
        
        # Setup History
        history_path = os.path.join(local_path, "setup_history.md")
        if os.path.exists(history_path):
            upload_queue.append((history_path, f"{project_name}/setup_history.md", "text/markdown"))
            
        # Project State
        upload_queue.append((state_file, f"{project_name}/project_state.json", "application/json"))

        # Folders to sync
        for folder in ['telemetry', 'setups', 'lapfiles', 'exports', 'reports']:
            folder_path = os.path.join(local_path, folder)
            if not os.path.exists(folder_path):
                continue
                
            for root, _, files in os.walk(folder_path):
                for f in files:
                    file_path = os.path.join(root, f)
                    if not os.path.isfile(file_path): continue
                    
                    # Calculate the relative path from the project root
                    # e.g. "exports/Daytona_2026/Aero.png"
                    rel_dir = os.path.relpath(root, local_path).replace('\\', '/')
                    remote_name = f
                    content_type = "application/octet-stream"
                    if f.lower().endswith('.png'): content_type = "image/png"
                    elif f.lower().endswith('.pdf'): content_type = "application/pdf"
                    
                    # Compress heavy telemetry files
                    if f.lower().endswith(('.ibt', '.ld')):
                        zip_path = file_path + ".zip"
                        print(f"  [#] Compressing {f}...", end="", flush=True)
                        import zipfile
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            zipf.write(file_path, arcname=f)
                        print(" DONE")
                        file_path = zip_path
                        remote_name = f + ".zip"
                        content_type = "application/zip"
                    
                    remote_path = f"{project_name}/{rel_dir}/{remote_name}"
                    upload_queue.append((file_path, remote_path, content_type))

        success_count = 0
        for local_file, remote_path, content_type in upload_queue:
            file_size_mb = os.path.getsize(local_file) / (1024 * 1024)
            print(f"  -> Uploading {os.path.basename(local_file)} ({file_size_mb:.1f} MB)...", end="", flush=True)
            
            upload_headers = {
                "apikey": self.anon_key,
                "Authorization": f"Bearer {self.token}",
                "Content-Type": content_type
            }
            
            try:
                with open(local_file, 'rb') as f_data:
                    # Using POST to upload new. Supabase returns 400 if it exists. 
                    # We should probably use PUT /storage/v1/object/opendav_assets/path to overwrite.
                    import urllib.parse
                    put_url = f"{bucket_url}/{urllib.parse.quote(remote_path)}"
                    res = requests.put(put_url, headers=upload_headers, data=f_data)
                    
                    if res.status_code in [200, 201]:
                        print(" OK")
                        success_count += 1
                    else:
                        # Fallback to POST if PUT fails (sometimes bucket policies require POST for new files)
                        post_url = f"{bucket_url}/{urllib.parse.quote(remote_path)}"
                        res_post = requests.post(post_url, headers=upload_headers, data=f_data)
                        if res_post.status_code in [200, 201]:
                            print(" OK")
                            success_count += 1
                        else:
                            print(f" FAILED ({res.status_code}: {res.text})")
                        if "exp" in res.text:
                            print("\n[!] Your login session has expired (Supabase tokens last 1 hour).")
                            print("    Please go to Settings -> Option 3 and Login again.")
                            return
            except Exception as e:
                print(f" ERROR ({e})")
                
                print(f"\n[+] Push complete. Synced {success_count}/{len(upload_queue)} files.")
        # Cleanup temporary local zips
        for local_file, _, _ in upload_queue:
            if local_file.endswith('.zip'):
                try: os.remove(local_file)
                except: pass

    def pull_project(self, project_name):
        if not self.is_logged_in():
            print("[!] You must be logged in to pull projects.")
            return
            
        print(f"\n[*] Pulling project '{project_name}' from OpenDAV Cloud...")
        
        search_url = f"{self.base_url}/storage/v1/object/list/opendav_assets"
        
        import analysis.projects as proj
        local_path = os.path.join(proj.PROJECTS_DIR, project_name)
        os.makedirs(local_path, exist_ok=True)
        for folder in ['telemetry', 'setups', 'lapfiles', 'exports', 'reports']:
            os.makedirs(os.path.join(local_path, folder), exist_ok=True)
            
        download_url = f"{self.base_url}/storage/v1/object/opendav_assets"
        
        # In Supabase Storage, the `list` endpoint only returns the direct children of the prefix.
        # We need to manually recurse into the folders.
        all_files = []
        folders_to_scan = [""] # root
        
        while folders_to_scan:
            current_folder = folders_to_scan.pop(0)
            prefix = f"{project_name}/{current_folder}" if current_folder else f"{project_name}"
            
            # The search path must end with a slash to list a directory in Supabase
            if not prefix.endswith("/"): prefix += "/"
                
            search_payload = {
                "prefix": prefix,
                "limit": 100,
                "offset": 0,
                "sortBy": {"column": "name", "order": "asc"}
            }
            
            try:
                r = requests.post(search_url, headers=self.get_headers(), json=search_payload)
                if r.status_code == 200:
                    for item in r.json():
                        if item['name'] == '.emptyFolderPlaceholder': continue
                        
                        # If it has no 'id' or 'metadata', it's a directory placeholder
                        if not item.get('id'):
                            folders_to_scan.append(os.path.join(current_folder, item['name']).replace('\\', '/'))
                        else:
                            item['full_path'] = os.path.join(current_folder, item['name']).replace('\\', '/')
                            all_files.append(item)
                else:
                    if not all_files: # Only print error if it's the root failure
                        print(f"  [!] Failed to locate project in cloud (Status {r.status_code}): {r.text}")
                        if "exp" in r.text:
                            print("\n[!] Your login session has expired (Supabase tokens last 1 hour).")
                            print("    Please go to Settings -> Option 3 and Login again.")
                        return
            except Exception as e:
                print(f"  [!] Network error: {e}")
                return
                
        if not all_files:
            print("  [!] No valid files found in this project bucket.")
            return

        success_count = 0
        for item in all_files:
            remote_file_path = f"{project_name}/{item['full_path']}"
            local_file_path = os.path.join(local_path, item['full_path'])
            
            # Ensure local subdirectories exist (e.g. telemetry/)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            
            print(f"  <- Downloading {item['name']}...", end="", flush=True)
            
            try:
                # GET request to download
                dl_res = requests.get(f"{download_url}/{remote_file_path}", headers={"apikey": self.anon_key, "Authorization": f"Bearer {self.token}"}, stream=True)
                
                if dl_res.status_code == 200:
                    with open(local_file_path, 'wb') as f_out:
                        for chunk in dl_res.iter_content(chunk_size=8192):
                            f_out.write(chunk)
                    
                    # Unzip telemetry
                    if local_file_path.lower().endswith('.zip'):
                        print(" Extracting...", end="", flush=True)
                        try:
                            import zipfile
                            with zipfile.ZipFile(local_file_path, 'r') as zip_ref:
                                zip_ref.extractall(os.path.dirname(local_file_path))
                            os.remove(local_file_path) # Clean up zip
                        except:
                            print(" ERROR (Zip)", end="")
                            
                    print(" OK")
                    success_count += 1
                else:
                    print(f" FAILED ({dl_res.status_code}: {dl_res.text})")
            except Exception as e:
                print(f" ERROR ({e})")
                
        print(f"\n[+] Pull complete. Downloaded {success_count} files to local workspace.")
