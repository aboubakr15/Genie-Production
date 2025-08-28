# myproject/db_routers.py
class AppBasedRouter:
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'ai_agent':  # Replace with your app name
            return 'railway'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == 'ai_agent':
            return 'railway'
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Force migrations for global_db app to go to the railway database
        if app_label == 'ai_agent':
            return db == 'railway'
        else:
            return db == 'default'
        return None
