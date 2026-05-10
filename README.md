### BFRN Marketplace Repository

# init submodule
git submodule update --init --recursive


> [!IMPORTANT]  
> django version: 5.2  
> python version: 3.11  
> docker-python version: 3.11-slim  


| TC | Description | Result |
|----|-------------|--------|
| TC-001 | Producers can register an account using their details and a secure password. |  PASS |
| TC-002 | Customers can create accounts with their personal information and delivery address to make purchases. |  PASS |
| TC-003 | Producers can create detailed product listings that include price, stock levels and seasonal availability. |  PASS |
| TC-004 | Customers can browse the marketplace by selecting specific product categories, such as vegetables or dairy. |  PASS |
| TC-005 | Customers can successfully search for specific items using product names or descriptions. |  PASS |
| TC-006 | Customers can add products to a shopping cart, modify quantities and see accurate price totals. |  PASS |
| TC-007 | Customers can complete the checkout process and payment for an order from a single producer. |  PASS |
| TC-008 | Customers can place a single multi-vendor order, which the system accurately splits by producer for delivery and payment. |  PASS |
| TC-009 | Producers can view a dashboard of their incoming orders, displaying customer details and delivery dates. |  PASS |
| TC-010 | Producers can update the status of their orders (e.g., Pending, Confirmed, Delivered) and trigger customer notifications. |  PASS |
| TC-011 | Producers can easily update their product stock quantities and availability status, immediately reflecting on the storefront. |  PASS |
| TC-012 | The system generates weekly payment settlements, distributing 95% of the order value to producers. |  PASS |
| TC-013 | The system calculates and displays the food miles between the producer's farm and the customer's delivery postcode. |  PASS |
| TC-014 | Customers can apply a filter to view only products that hold an organic certification. |  PASS |
| TC-015 | Products clearly display necessary allergen warnings to ensure customer safety and regulatory compliance. |  PASS |
| TC-016 | Producers can set specific date ranges for seasonal products and the system automatically shows relevant availability badges. |  PASS |
| TC-017 | Community groups can register institutional accounts and place large bulk orders across multiple producers. |  PASS |
| TC-018 | Restaurants and business accounts can set up automated, recurring weekly orders for local ingredients. |  PASS |
| TC-019 | Producers can mark excess inventory as surplus, applying a discount percentage to help reduce food waste. |  PASS |
| TC-020 | Producers can publish farm stories and recipes linked to their products to engage with the community. |  PASS |
| TC-021 | Customers can view their complete order history and easily duplicate past purchases using a reorder function. |  PASS |
| TC-022 | The system enforces secure authentication, password hashing and role-based access control for all users. |  PASS |
| TC-023 | Producers receive automated low-stock notifications when their inventory drops below a customisable threshold. |  PASS |
| TC-024 | Customers can leave star ratings and text reviews exclusively on products from orders that have been successfully delivered. |  PASS |
| TC-025 | System administrators can generate financial reports to audit the 5% network commission and producer payouts. |  PASS |



											
> [!NOTE]  
> Latest changes (based on https://www.youtube.com/watch?v=37aNpE-9dD4):
> ```bash
> // Hard Reset script
> // Deletes and rebuilds docker containers from scratch.
> // Additionally creates django superuser (root@example.com, Password123), makes migrations and boots system.
> 
> // WINDOWS
> .\scripts\hard_reset_server.bat
> // UNIX
> bash ./scripts/hard_reset_server.sh 
> 
> // To run & build the system:
> docker compose up --build 
> 
> Steps project went through:
>
> // created draft project
> django-admin startproject marketplace_platform
> 
> // created app inside project
> python .\manage.py startapp core
> 
> // (open new terminal) execute commands inside container
> // makemigrations is needed when app/models.py gets changed
> docker exec django_app python manage.py makemigrations
> // all migrations made in container will be updated in local files as well (based on where VOLUME is defined)
> docker exec django_app python manage.py migrate
>
> // create django superuser (for admin functionality)
> docker exec -it django_app python manage.py createsuperuser
> 
> // enters postgres CLI utility, -U user -d database
> docker exec -ti postgres_db psql -U myuser -d mydb
>
> // create a superuser
> docker compose exec web python manage.py createsuperuser
> ```


## User Roles and Credentials for Testing Login

| Role   | Username   | Password    |
|--------|------------|-------------|
| admin  | admin      | Password123    |
| producer   | producer@example.com   | Password123 |
| community | community@example.com     | Password123    |
| restaurant | restaurant@example.com     | Password123    |
| customer  | customer@example.com      | Password123   |

<details>
<summary><b> &nbsp Repository Architecture (File tree)</b>
</summary>
<br/>
<blockquote>

```
.
├── architecture.md # Main file detailing repository architecture
├── docker-compose.yml # Docker Compose configuration file
├── Dockerfile # Dockerfile for building the application image
├── LICENSE # License information file
├── marketplace_platform # Main Django application for the marketplace platform
│   ├── api # API app for the marketplace platform
│   │   ├── admin.py # Django admin configurations for the API app
│   │   ├── apps.py # Application configuration for the API app
│   │   ├── __init__.py # Initializes the API package
│   │   ├── migrations # Database migration files for the API app
│   │   ├── models.py # Database models for the API app
│   │   ├── __pycache__ # Cache directory for Python modules
│   │   ├── tests.py # Tests for the API app
│   │   ├── urls.py # URL configurations for the API app
│   │   └── views.py # API views (endpoints) for the marketplace platform
│   ├── api_requirements.txt # Specific package dependencies for the API
│   ├── core # Core functionalities and utilities for the marketplace platform
│   │   ├── admin.py # Django admin configurations for the core app
│   │   ├── apps.py # Application configuration for the core app
│   │   ├── backends.py # Custom authentication backends
│   │   ├── context_processors.py # Django template context processors
│   │   ├── forms.py # Django forms for the core app
│   │   ├── __init__.py # Initializes the core package
│   │   ├── management # Custom Django management commands
│   │   ├── migrations # Database migration files for the core app
│   │   ├── models.py # Database models for the core app
│   │   ├── module # Module related to location data
│   │   ├── permissions.py # Custom permission classes
│   │   ├── __pycache__ # Cache directory for Python modules
│   │   ├── static # Static files (CSS, JS, images) for the core app
│   │   ├── templates # HTML templates for the core app
│   │   ├── templatetags # Custom Django template tags
│   │   ├── tests.py # Tests for the core app
│   │   ├── urls.py # URL configurations for the core app
│   │   ├── utils.py # Utility functions for the core app
│   │   └── views.py # Core views for the marketplace platform
│   ├── database_interactions.log # Log file for database interactions
│   ├── manage.py # Django command-line utility script
│   ├── marketplace_platform # Django project settings and configurations
│   │   ├── asgi.py # ASGI configuration
│   │   ├── __init__.py # Initializes the marketplace_platform package
│   │   ├── __pycache__ # Cache directory for Python modules
│   │   ├── settings.py # Django project settings
│   │   ├── urls.py # Django project URL configurations
│   │   └── wsgi.py # WSGI configuration
│   ├── media # User-uploaded media files
│   │   ├── CACHE # Cache directory for media
│   │   └── item_images # Images for marketplace items
│   ├── requirements.txt # Project dependencies
│   └── synthetic_data # Scripts and data for generating synthetic test data
│       ├── alter_order_pids.py # Script to alter order PIDs
│       ├── archive # Archive directory for old data
│       ├── orders.csv # Order data
│       ├── ordersold2.csv # Another old order data file
│       ├── products.csv # Product data
│       ├── productsold2.csv # Another old product data file
│       └── users.csv # User data
├── README.md # Top-level README file for the project
├── scripts # Utility scripts for development and deployment
│   ├── hard_reset_server.bat # Windows script for hard server reset
│   ├── hard_reset_server.sh # Linux/macOS script for hard server reset
│   ├── restart_migration.bat # Windows script for restart migration
│   ├── restart_migration.sh # Linux/macOS script for restart migration
│   └── restart_server.bat # Windows script for server restart
└── security_changes.md # Document detailing security-related changes
```

</blockquote>
</details>
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
      <td><strong>starts server (default localhost:8111)</strong></td>
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
      <td><strong>define website paths/routes (like localhost:8111/admin)</strong></td>
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

</details>

<details>
<summary><b> &nbsp Tech stack </b>
</summary>

| Tool     | Use                                                           |
|----------|---------------------------------------------------------------|
| Jira     | Managing individual duties and deadlines            |
| Overleaf | Real-time collaboration on reports and documentation |
| Docker   | Hosting and running the application                 |
| Python   | Programming language used for development               |
##### Libraries
| Tool         | Use                                                                                 | Version |
|--------------|-------------------------------------------------------------------------------------|---------|
| scikit-learn | Library that provides the machine learning resources used in the application       |         |
| numpy        | Handling and calculating with various data structures                     |         |
| pandas       | Handling large data structures and CSV files                              |         |
| django       | High level web framework used for handling web applications | 3.11    |
| psycopg2     | Connecting Python to PostgreSQL for database management                   | 2.9.11  |
| docker       | Connecting Python to Docker                                               |         |
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





