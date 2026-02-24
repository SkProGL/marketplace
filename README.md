### Draft repository

> [!NOTE]  
> Latest changes (based on https://www.youtube.com/watch?v=37aNpE-9dD4):
> ```bash
> // created draft project
> django-admin startproject marketplace_platform
> 
> // created app inside project
> python .\manage.py startapp core
>
> // run & build container
> docker compose up --build 
> 
> // (open new terminal) execute commands inside container
> // makemigrations is needed when app/models.py gets changed
> docker exec django_app python manage.py makemigrations
> // all migrations made in container will be updated in local files as well (based on where VOLUME is defined)
> docker exec django_app python manage.py migrate
>
> // enters postgres CLI utility, -U user -d database
> docker exec -ti postgres_db psql -U myuser -d mydb
> ```

> [!IMPORTANT]  
> django version: 5.2  
> python version: 3.11  
> docker-python version: 3.11-slim  


<details>
<summary><b> &nbsp Python </b>
</summary>
    <div>
<br/>
<table>
  <thead>
    <tr>
      <th>Step</th>
      <th>Command</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>1.1 create uv environment</strong></td>
      <td><code>uv venv --python 3.11</code></td>
    </tr>
    <tr>
      <td><strong>activate (windows)</strong></td>
      <td><code>.\.venv\Scripts\activate</code></td>
    </tr>
    <tr>
      <td><strong>activate (linux / macos)</strong></td>
      <td><code>source .venv/bin/activate</code></td>
    </tr>
    <tr>
      <td><strong>1.2 install packages (same as pip)</strong></td>
      <td><code>uv pip install django</code></td>
    </tr>
    <tr>
      <td><strong>1.3 deactivate environment</strong></td>
      <td><code>deactivate</code></td>
    </tr>
  </tbody>
</table>
    </div>
</details>

<details>

<summary><b> &nbsp Django</b>
</summary>
<br/>
<div>Django has only one project, but can have many apps.</div>
<br/>
<table>
  <tbody>
    <tr>
      <td colspan="2"><strong>Admin commands</strong></td>
    </tr>
    <tr>
      <td><code>django-admin</code></td>
      <td><strong>view full list of commands</strong></td>
    </tr>
    <tr>
      <td><code>django-admin startproject project_name</code></td>
      <td><strong>template project</strong></td>
    </tr>
  </tbody>
</table>
    <table>
  <tbody>
    <tr>
      <td colspan="2"><strong>Server management</strong></td>
    </tr>
    <tr>
      <td><code>python manage.py runserver</code></td>
      <td><strong>starts server (default localhost:8000)</strong></td>
    </tr>
    <tr>
      <td><code>python manage.py startapp blog</code></td>
      <td><strong>creates new app</strong></td>
    </tr>
    <tr>
      <td><code>python manage.py makemigrations</code></td>
      <td></td>
    </tr>
  </tbody>
</table>
<table>
  <tbody>
    <tr>
      <td colspan="2"><strong>Script / folder purpose:</strong></td>
    </tr>
    <tr>
      <td><code>project/urls.py</code></td>
      <td><strong>define website paths/routes (like localhost:8000/admin)</strong></td>
    </tr>
    <tr>
      <td><code>app/urls.py</code></td>
      <td><strong>points to page of that app</strong></td>
    </tr>
    <tr>
      <td><code>app/views.py</code></td>
      <td><strong>returns HttpResponse with html page</strong></td>
    </tr>
    <tr>
      <td><code>app/models.py</code></td>
      <td><strong>creates a database model (need to apply migrations when changed), model can be anything (sql, sqlite3)</strong></td>
    </tr>
    <tr>
      <td><code>app/templates</code></td>
      <td><strong>contains .html pages</strong></td>
    </tr>
    <tr>
      <td><code>app/static</code></td>
      <td><strong>contains .css, .js files and images</strong></td>
    </tr>
    <tr>
      <td><code>project/settings.py</code></td>
      <td><strong>specifies links to app config</strong></td>
    </tr>
  </tbody>
</table>
</details>

<details>
<summary><b> &nbsp Docker</b>
</summary>
<br/>
<blockquote>
to specify python version in docker, use slim build <br/>
FROM python:3.11-slim
</blockquote>
</details>


<details>
<summary><b> &nbsp Github task workflow</b>
</summary>

## Prerequistes:
- Repository is cloned with `git clone <repo_url>`
- Decide on assigned JIRA task and set it to _In-progress_  (i.e., Create login page)

## Creating a Branch:
1. **Ensure local main is up-to-date with remote**
	```bash
    git switch main
    git fetch
    git pull origin main
    ```

2. **Create a new branch with:**

	```bash
    git checkout -b <prefix/branch_name> 
    # OR
    git switch -c <prefix/branch_name>
    ```

    | prefix  |  Purpose |
    |---|---|
    | **main**   | Main development branch  |
    | **feature/**  |  New features (e.g., feature/add-login-page, feat/add-login-page) |
    | **bugfix/** |  Bug fixes (e.g., bugfix/fix-header-bug, fix/header-bug) |
    |**chore/**: | For non-code tasks like dependency, docs updates (e.g., chore/update-dependencies) |


## Making changes
1. **Change to your branch and ensure it is up-to-date** 
    ```bash
        git switch <branch_name>
        git fetch
        git pull origin <branch_name>
    ```

2. **Commit local changes to remote**
    - Try to make modular commits over commiting large amounts of changes at once.

    - Ideally do not `git add . ` unless all changed files directly relate to the commit message.
    - **Commit messages should start with imperative verb.** 
    
        Example:
        "_Add button_", "_Update field_" or "_Delete variable_" .
    ```bash
    git branch                  # Verify that you are on the right branch
    git add "<changed_files>"
    git commit -m "<message>"
    ```


3. **Push changes to remote**
    ```bash
    git push origin <current_branch>
    ```

    - **IMPORTANT:** main may have updated since creating your branch, regularly **_merge_*** with
    ```bash 
    git fetch origin main        # Get up-to-date main from remote.       
    git merge origin/main                   
    git push origin <current_branch> 
    
    # You may be prompted to handle conflicts.
    # If so, resolve the conflicts and
    git add <resolved_files>
    git commit
    git push origin <current_branch>
    ```


4. **Once the task is complete. Create a pull request (PR) from the _<current_branch>_ to _main_.** Then:
    1. Describe what your PR implements or fixes. (e.g., "This PR ...") with fitting title (e.g., "Feature: Add Thing... ").

    2. Add other developers as reviewers and await their review.
        - Apply feedback as applicable.
    3. Once approved, select **_merge and squash_** with a descriptive commit message (e.g, "This commit ... ").
    4. Once merged, delete the branch **when the prompt says it is safe to do so**.

<br>

---

<br>

### Rebasing

*If working on a branch alone you can opt for **_rebase_** instead of **_merge_** for a cleaner linear git history:

``` bash
git fetch origin main                           
git rebase origin/main             # Takes new main and places your branch's history on top
git push --force-with-lease origin <current_branch> # DO NOT PULL. Force the rewritten history. 

# Resolve conflicts as necessary
git add <resolved_files>
git rebase --continue
# ...
git push --force-with-lease origin <current_branch> 
```

![alt text](image.png)

*Example diagram*
</details>

### Running pages 
- use "python manage.py runserver" to preview pages in browser 