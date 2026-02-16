### Draft repository

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
