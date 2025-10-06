class AppDatabaseRouter:
    """
    Routes models from specific apps to specific databases.
    """

    def db_for_read(self, model, **hints):
        """Point all read operations."""
        if model._meta.app_label == 'ai_agent':  # replace with your app name
            return 'global'
        return 'default'

    def db_for_write(self, model, **hints):
        """Point all write operations."""
        if model._meta.app_label == 'ai_agent':  # replace with your app name
            return 'global'
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations if both models are in the same DB."""
        db_set = {'default', 'global'}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """Ensure migrations only apply to the right DB."""
        if app_label == 'ai_agent':  # replace with your app name
            return db == 'global'
        return db == 'default'
