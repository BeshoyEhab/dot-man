# **dot-man: Project & Architecture Guide**

## **1\. Project Goal & Tech Stack**

Your goal is to build a standalone Python CLI tool to manage dotfiles. It will use a hidden git repo for versioning and branching, and it will be smart enough to auto-discover files and filter secrets.

**Selected Tech Stack:**

* **click (for CLI):** We'll use this instead of argparse. Its decorator-based system (@click.command()) is much cleaner for defining commands, arguments, and options. It automatically generates beautiful help menus.  
* **GitPython (for Git):** We'll use this instead of subprocess. This is the most critical upgrade. It gives you an object-oriented way to interact with git. Instead of parsing stderr text, you can use Python's try...except blocks to catch specific git errors, like merge conflicts. This makes your sync command *dramatically* more robust.  
* **rich (for UI):** We'll use this instead of print(). It provides easy, beautiful terminal colors, formatting, and—most importantly—tables, which are perfect for the dot-man status command.  
* **Standard Library:** configparser (for .ini files), pathlib (for file paths), shutil (for file I/O), and re (for secrets).

## **2\. Core Project Structure**

The file/folder layout remains the same. Your script will manage this structure at \~/.config/dot-man/:

\~/.config/dot-man/  
├── repo/           \<-- The GitPython.Repo object will point here  
│   ├── .git/  
│   ├── dot-man.ini  
│   └── ... (mirrored dotfiles)  
│  
└── global.conf     \<-- Stores the 'current\_branch'

## **3\. Implementation Guide (The "How-To")**

Here is the step-by-step logic for building each command.

#### **dot-man init**

1. **Click:** Define a @click.command() function.  
2. **Logic:**  
   * Use pathlib.Path.mkdir(parents=True, exist\_ok=True) to create \~/.config/dot-man and \~/.config/dot-man/repo.  
   * **Init Repo:** Use git.Repo.init(REPO\_DIR) to initialize the empty repository. This gives you a repo object.  
   * **Create global.conf:** Use configparser to create a new config, set \[dot-man\] current\_branch \= main, and write it to GLOBAL\_CONFIG\_FILE.  
   * **First Commit:** Write a default dot-man.ini file (as a string) into REPO\_DIR. Use repo.git.add('.') and repo.index.commit('dot-man: Initial commit') to create the main branch.  
   * **UI:** Use rich.console.print("\[green\]Success\!\[/green\] dot-man initialized.") for feedback.

#### **dot-man switch \<branch-name\>**

This is your main command. It's a two-phase operation: **(1) Save, (2) Deploy.**

1. **Click:** Define a function with @click.argument('branch\_name').  
2. **Get State:**  
   * Load the repo object: repo \= git.Repo(REPO\_DIR).  
   * Get the from\_branch by reading global.conf with configparser.  
   * If from\_branch \== branch\_name, just print "Already on branch" and exit.  
3. **Phase 1: Save Local Changes (\_save\_local\_changes)**  
   * This is a helper function you'll write.  
   * **Load Config:** Read the dot-man.ini *currently* in the repo.  
   * **Iterate Sections:** Loop through each \[section\] in the .ini.  
   * **File Discovery Logic:** For each section:  
     * Get the local\_path (e.g., \~/config/nvim) and repo\_path (e.g., \~/.config/dot-man/repo/.config/nvim).  
     * **Check for Deletions:** If repo\_path exists but local\_path doesn't, the user deleted it. Use shutil.rmtree(repo\_path) or repo\_path.unlink().  
     * **Check for Add/Modify:** If local\_path exists:  
       * If it's a file: Call a \_copy\_file\_to\_repo helper.  
       * If it's a dir: Use local\_path.rglob('\*') to walk *all* files inside. For each file, calculate its destination path in the repo (using file.relative\_to(local\_path)) and call your \_copy\_file\_to\_repo helper.  
   * **\_copy\_file\_to\_repo(src\_path, dest\_path, secrets\_config):**  
     * This helper checks the secrets\_filter config.  
     * If False, just shutil.copy2(src\_path, dest\_path).  
     * If True: Read src\_path.read\_text(). Use re.sub() with your secrets regex to create redacted\_content. Then dest\_path.write\_text(redacted\_content). **This is the core secrets logic.**  
   * **Commit Changes:** After iterating all sections, check if the repo is dirty: if repo.is\_dirty(untracked\_files=True):.  
   * If it is, use repo.git.add('.') and repo.index.commit(f'Auto-save on {from\_branch}').  
4. **Phase 2: Switch & Deploy (\_deploy\_branch\_files)**  
   * **Switch Branch:**  
     * Check if branch\_name exists in repo.heads.  
     * If yes: repo.git.checkout(branch\_name).  
     * If no: repo.create\_head(branch\_name).checkout().  
   * **Deploy Files:**  
     * This is a new helper, \_deploy\_branch\_files.  
     * **Load *New* Config:** The git checkout just swapped your dot-man.ini. Load it again with configparser.  
     * **Iterate Sections:** Loop through the new config.  
     * Get the update strategy. If "ignore", continue.  
     * Define local\_path and repo\_path.  
     * **Handle rename\_old:** If strategy is rename\_old and local\_path exists, use shutil.move(local\_path, f"{local\_path}.old").  
     * **Handle replace:** Use shutil.copytree(repo\_path, local\_path, dirs\_exist\_ok=True) for dirs or shutil.copy2(repo\_path, local\_path) for files.  
   * **Update State:** Use configparser to write current\_branch \= branch\_name to global.conf.  
   * **UI:** Print \[green\]Switched to {branch\_name}\[/green\].

#### **dot-man sync**

This is where GitPython is a lifesaver.

1. **Click:** Define the command with options for \--force-pull, \--force-push, and \--continue.  
2. **Get Remote:** repo \= get\_repo(), then origin \= repo.remotes.origin. (Add a try...except IndexError in case origin isn't set).  
3. **Handle Force Pull:** If \--force-pull, use rich.prompt.Confirm.ask() in red. If yes, run repo.git.fetch(origin) and repo.git.reset('--hard', f'origin/{get\_current\_branch()}'). Then call \_deploy\_branch\_files() to update your home dir.  
4. **Handle Force Push:** If \--force-push, get confirmation. If yes, call \_save\_local\_changes() first, then origin.push(force=True).  
5. **Standard Sync:**  
   * **Step 1 (Save):** Call \_save\_local\_changes().  
   * **Step 2 (Pull):** This is the key. Wrap it in a try...except:  
     try:  
         origin.pull()  
     except git.exc.GitCommandError as e:  
         if "merge conflict" in str(e).lower():  
             console.print("\[red\]Merge conflict detected\!\[/red\]")  
             console.print(f"Fix conflicts in: {REPO\_DIR}")  
             console.print("Then run 'dot-man sync \--continue'")  
         else:  
             console.print(f"\[red\]Error: {e}\[/red\]")  
         sys.exit(1)

   * **Step 3 (Continue):** If sync is run with \--continue, you just need to repo.index.commit("Resolved merge") (because git add should have been done by the user).  
   * **Step 4 (Push):** Call origin.push().

#### **dot-man status**

1. **Click:** Define the command.  
2. **UI:** Create a rich.table.Table.  
3. **Logic:**  
   * repo \= get\_repo().  
   * Add rows to the table: "Current Branch", "Repo Dirty (repo.is\_dirty())".  
   * **Dry Run:** This is the hard part. You need to implement the "diff" logic.  
   * **Diff Logic:**  
     * Create a "dry run" version of \_save\_local\_changes.  
     * Walk the files just like switch does.  
     * For each file, *compare* it instead of copying.  
     * If repo\_path exists but local\_path doesn't \-\> "Removed".  
     * If local\_path exists but repo\_path doesn't \-\> "New".  
     * If both exist, read both and compare. A simple local\_path.read\_bytes() \!= repo\_path.read\_bytes() works. If different \-\> "Modified".  
     * **For secrets:** If secrets\_filter \= True and files are different, show "Modified (Secrets)".  
     * Add each finding to your rich table.  
   * Print the table.

#### **dot-man branch**

This command manages the git branches within the repo.

1. **Click:** Define a command group: @click.group() def branch(): ...  
2. **List Command (branch list):**  
   * Define a subcommand: @branch.command(name='list').  
   * **Logic:**  
     * repo \= get\_repo().  
     * current\_branch \= get\_current\_branch().  
     * Use rich to create a Table with columns "Branch" and "Active".  
     * Iterate through repo.heads:  
       * For each head (branch) in repo.heads:  
         * If head.name \== current\_branch, add a row with (head.name, "\*").  
         * Otherwise, add a row with (head.name, "").  
     * Print the rich table.  
3. **Delete Command (branch delete \<branch-name\>):**  
   * Define a subcommand: @branch.command(name='delete') with @click.argument('branch\_name').  
   * **Logic:**  
     * repo \= get\_repo().  
     * current\_branch \= get\_current\_branch().  
     * **Safety Check:** If branch\_name \== current\_branch, print an error ("Cannot delete the active branch") and exit.  
     * **Confirmation:** Use rich.prompt.Confirm.ask(f"Are you sure you want to delete branch '{branch\_name}'?").  
     * If confirmed, use git.Repo.delete\_head(branch\_name, force=True). Wrap this in a try...except to catch errors if the branch doesn't exist.  
     * Print a success message.

#### **dot-man remote**

This command manages the git remote URL.

1. **Click:** Define a command group: @click.group() def remote(): ...  
2. **Get Command (remote get):**  
   * Define a subcommand: @remote.command(name='get').  
   * **Logic:**  
     * repo \= get\_repo().  
     * Use a try...except block with IndexError (for when 'origin' doesn't exist).  
     * origin \= repo.remotes.origin.  
     * console.print(origin.url).  
     * If IndexError, print "No remote 'origin' set."  
3. **Set Command (remote set \<url\>):**  
   * Define a subcommand: @remote.command(name='set') with @click.argument('url').  
   * **Logic:**  
     * repo \= get\_repo().  
     * Use a try...except block with IndexError.  
     * **If remote exists:** origin \= repo.remotes.origin, then origin.set\_url(url). Print "Updated remote 'origin'."  
     * **If remote doesn't exist:** repo.create\_remote('origin', url). Print "Created remote 'origin'."

#### **dot-man edit**

This command provides a shortcut to edit the *current* branch's configuration file.

1. **Click:** Define a simple command: @click.command()  
2. **Logic:**  
   * **Get Editor:** Get the user's preferred editor. Check os.environ.get('EDITOR'). If it's not set, default to nano or vim.  
   * **Get File Path:** config\_file \= REPO\_DIR / 'dot-man.ini'.  
   * **Run Editor:** This is the key. Use click.edit(filename=str(config\_file), editor=editor\_name). click has a built-in helper for this which is much safer than subprocess.run. It will wait for the editor to close before continuing.  
   * Print a message: "Config file opened. 'dot-man status' may show changes."

#### **dot-man deploy \<branch-name\>**

This is the "new machine" bootstrap command. It's a one-way sync from the repo to the home directory.

1. **Click:** Define a command: @click.command() with @click.argument('branch\_name').  
2. **Logic:**  
   * repo \= get\_repo().  
   * **Checkout:** repo.git.checkout(branch\_name).  
   * **Confirm:** Use rich.prompt.Confirm.ask() to warn the user this will overwrite local files.  
   * **Load Config:** Load the dot-man.ini for the specified branch.  
   * **Deploy Logic:**  
     * This is a simplified version of \_deploy\_branch\_files from the switch command.  
     * Iterate through all sections in the config.  
     * **IMPORTANT:** *Ignore all update strategies.* The point of deploy is to force-overwrite.  
     * For each section, get repo\_path and local\_path.  
     * Create parent directories: local\_path.parent.mkdir(parents=True, exist\_ok=True).  
     * Use shutil.copytree(repo\_path, local\_path, dirs\_exist\_ok=True) for dirs or shutil.copy2(repo\_path, local\_path) for files.  
   * **Final Step:** Call set\_current\_branch(branch\_name).  
   * Print \[green\]Deployment of '{branch\_name}' complete.\[/green\].