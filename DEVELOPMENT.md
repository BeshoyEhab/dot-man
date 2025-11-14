# **dot-man: Project & Architecture Guide**

## **1. Project Goal & Tech Stack**

Your goal is to build a standalone Python CLI tool to manage dotfiles. It will use a hidden git repo for versioning and branching, and it will be smart enough to auto-discover files and filter secrets.

**Selected Tech Stack:**

* **click (for CLI):** We'll use this instead of argparse. Its decorator-based system (@click.command()) is much cleaner for defining commands, arguments, and options. It automatically generates beautiful help menus.  
* **GitPython (for Git):** We'll use this instead of subprocess. This is the most critical upgrade. It gives you an object-oriented way to interact with git. Instead of parsing stderr text, you can use Python's try...except blocks to catch specific git errors, like merge conflicts. This makes your sync command *dramatically* more robust.  
* **rich (for UI):** We'll use this instead of print(). It provides easy, beautiful terminal colors, formatting, and—most importantly—tables, which are perfect for the dot-man status command.  
* **Standard Library:** configparser (for .ini files), pathlib (for file paths), shutil (for file I/O), and re (for secrets).

## **2. Core Project Structure**

The file/folder layout remains the same. Your script will manage this structure at ~/.config/dot-man/:

~/.config/dot-man/  
├── repo/           <-- The GitPython.Repo object will point here  
│   ├── .git/  
│   ├── dot-man.ini  
│   └── ... (mirrored dotfiles)  
│  
└── global.conf     <-- Stores the 'current_branch'

## **3. Implementation Guide (The "How-To")**

Here is the step-by-step logic for building each command.

#### **dot-man init**

1. **Click:** Define a @click.command() function.  
2. **Logic:**  
   * Use pathlib.Path.mkdir(parents=True, exist_ok=True) to create ~/.config/dot-man and ~/.config/dot-man/repo.  
   * **Init Repo:** Use git.Repo.init(REPO_DIR) to initialize the empty repository. This gives you a repo object.  
   * **Create global.conf:** Use configparser to create a new config, set [dot-man] current_branch = main, and write it to GLOBAL_CONFIG_FILE.  
   * **First Commit:** Write a default dot-man.ini file (as a string) into REPO_DIR. Use repo.git.add('.') and repo.index.commit('dot-man: Initial commit') to create the main branch.  
   * **UI:** Use rich.console.print("[green]Success![/green] dot-man initialized.") for feedback.

#### **dot-man switch <branch-name>**

This is your main command. It's a two-phase operation: **(1) Save, (2) Deploy.**

1. **Click:** Define a function with @click.argument('branch_name').  
2. **Get State:**  
   * Load the repo object: repo = git.Repo(REPO_DIR).  
   * Get the from_branch by reading global.conf with configparser.  
   * If from_branch == branch_name, just print "Already on branch" and exit.  
3. **Phase 1: Save Local Changes (_save_local_changes)**  
   * This is a helper function you'll write.  
   * **Load Config:** Read the dot-man.ini *currently* in the repo.  
   * **Iterate Sections:** Loop through each [section] in the .ini.  
   * **File Discovery Logic:** For each section:  
     * Get the local_path (e.g., ~/config/nvim) and repo_path (e.g., ~/.config/dot-man/repo/.config/nvim).  
     * **Check for Deletions:** If repo_path exists but local_path doesn't, the user deleted it. Use shutil.rmtree(repo_path) or repo_path.unlink().  
     * **Check for Add/Modify:** If local_path exists:  
       * If it's a file: Call a _copy_file_to_repo helper.  
       * If it's a dir: Use local_path.rglob('*') to walk *all* files inside. For each file, calculate its destination path in the repo (using file.relative_to(local_path)) and call your _copy_file_to_repo helper.  
   * **_copy_file_to_repo(src_path, dest_path, secrets_config):**  
     * This helper checks the secrets_filter config.  
     * If False, just shutil.copy2(src_path, dest_path).  
     * If True: Read src_path.read_text(). Use re.sub() with your secrets regex to create redacted_content. Then dest_path.write_text(redacted_content). **This is the core secrets logic.**  
   * **Commit Changes:** After iterating all sections, check if the repo is dirty: if repo.is_dirty(untracked_files=True):.  
   * If it is, use repo.git.add('.') and repo.index.commit(f'Auto-save on {from_branch}').  
4. **Phase 2: Switch & Deploy (_deploy_branch_files)**  
   * **Switch Branch:**  
     * Check if branch_name exists in repo.heads.  
     * If yes: repo.git.checkout(branch_name).  
     * If no: repo.create_head(branch_name).checkout().  
   * **Deploy Files:**  
     * This is a new helper, _deploy_branch_files.  
     * **Load *New* Config:** The git checkout just swapped your dot-man.ini. Load it again with configparser.  
     * **Iterate Sections:** Loop through the new config.  
     * Get the update strategy. If "ignore", continue.  
     * Define local_path and repo_path.  
     * **Handle rename_old:** If strategy is rename_old and local_path exists, use shutil.move(local_path, f"{local_path}.old").  
     * **Handle replace:** Use shutil.copytree(repo_path, local_path, dirs_exist_ok=True) for dirs or shutil.copy2(repo_path, local_path) for files.  
   * **Update State:** Use configparser to write current_branch = branch_name to global.conf.  
   * **UI:** Print [green]Switched to {branch_name}[/green].

#### **dot-man sync**

This is where GitPython is a lifesaver.

1. **Click:** Define the command with options for --force-pull, --force-push, and --continue.  
2. **Get Remote:** repo = get_repo(), then origin = repo.remotes.origin. (Add a try...except IndexError in case origin isn't set).  
3. **Handle Force Pull:** If --force-pull, use rich to Confirm.ask() in red. If yes, run repo.git.fetch(origin) and repo.git.reset('--hard', f'origin/{current_branch}'). Then call _deploy_branch_files() to update your home dir.  
4. **Handle Force Push:** If --force-push, get confirmation. If yes, call _save_local_changes() first, then origin.push(force=True).  
5. **Standard Sync:**  
   * **Step 1 (Save):** Call _save_local_changes().  
   * **Step 2 (Pull):** This is the key. Wrap it in a try...except:  
     try:  
         origin.pull()  
     except git.exc.GitCommandError as e:  
         if "merge conflict" in str(e).lower():  
             console.print("[red]Merge conflict detected![/red]")  
             console.print(f"Fix conflicts in: {REPO_DIR}")  
             console.print("Then run 'dot-man sync --continue'")  
         else:  
             console.print(f"[red]Error: {e}[/red]")  
         sys.exit(1)

   * **Step 3 (Continue):** If sync is run with --continue, you just need to repo.index.commit("Resolved merge") (because git add should have been done by the user).  
   * **Step 4 (Push):** Call origin.push().

#### **dot-man status**

1. **Click:** Define the command.  
2. **UI:** Create a rich.table.Table.  
3. **Logic:**  
   * repo = get_repo().  
   * Add rows to the table: "Current Branch", "Repo Dirty (repo.is_dirty())".  
   * **Dry Run:** This is the hard part. You need to implement the "diff" logic.  
   * **Diff Logic:**  
     * Create a "dry run" version of _save_local_changes.  
     * Walk the files just like switch does.  
     * For each file, *compare* it instead of copying.  
     * If repo_path exists but local_path doesn't -> "Removed".  
     * If local_path exists but repo_path doesn't -> "New".  
     * If both exist, read both and compare. A simple local_path.read_bytes() != repo_path.read_bytes() works. If different -> "Modified".  
     * **For secrets:** If secrets_filter = True and files are different, show "Modified (Secrets)".  
     * Add each finding to your rich table.  
   * Print the table.
