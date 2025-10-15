## Welcome to the IBH Genie-Production codebase!

This document provides guidance for AI coding agents to effectively contribute to this project.

### Project Overview

This is a Django-based CRM application designed to manage leads, sales, and operations. The project is divided into several Django apps, each corresponding to a specific user role or functionality.

- **`main`**: Core functionalities like authentication, notifications, and general views.
- **`leads`**: Manages leads, including uploading, processing, and assigning them.
- **`sales`**: Functionality for the sales team.
- **`sales_manager`**: Functionality for sales managers.
- **`operations_manager`**: Functionality for operations managers.
- **`administrator`**: Admin-specific functionalities.
- **`api`**: Provides a RESTful API.
- **`ai_agent`**: Handles AI-related tasks.

### Key Files and Directories

- **`IBH/settings.py`**: The main Django settings file. It contains database configurations, installed apps, and other project-level settings. Note the use of multiple databases (`default` and `global`) and a `DATABASE_ROUTERS` to manage them.
- **`IBH/urls.py`**: The root URL configuration. It includes URLs from each app, organized by namespaces.
- **`templates/`**: Contains all the HTML templates for the project, organized into subdirectories for each app.
- **`static/`**: Contains static assets like CSS, JavaScript, and images.
- **`manage.py`**: The Django command-line utility for administrative tasks.

### Development Workflow

1.  **Environment Setup**: The project uses a virtual environment. Make sure to activate it before running any commands:
    ```bash
    .\env\Scripts\activate
    ```
2.  **Running the Development Server**:
    ```bash
    python manage.py runserver
    ```
3.  **Running Tests**:
    ```bash
    python manage.py test
    ```

### Code Conventions

- **Models**: Models are defined in the `models.py` file of main & ai_agents apps. Each represent a database schema.
- **Views**: Views are defined in the `views.py` file of each app. They contain the business logic for handling HTTP requests.
- **Templates**: Templates are located in the `templates/` directory and are organized by app.
- **Forms**: Forms are defined in the `forms.py` file of each app.
- **URLs**: URLs are defined in the `urls.py` file of each app and are included in the root `IBH/urls.py`.

### Important Patterns

- **Role-Based Access Control**: The application uses Django's built-in groups and permissions to control access to different parts of the application. The user's group determines their role and the views they can access.
- **Database Routing**: The project uses a database router (`IBH/database_router.py`) to direct database queries to the appropriate database based on the app.
- **Celery for Background Tasks**: The `ai_agent` and `leads` apps use Celery for running background tasks. See `tasks.py` in these apps for examples.

### Example: Adding a new view

To add a new view, you would typically need to:

1.  Create a new function or class-based view in the `views.py` of the relevant app.
2.  Create a new HTML template in the `templates/<app_name>/` directory.
3.  Add a new URL pattern to the `urls.py` of the app.

By following these guidelines, you should be able to contribute effectively to the project. If you have any questions, please refer to the existing code for examples.
