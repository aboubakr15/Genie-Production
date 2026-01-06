import logging

ADMIN_LEVEL_NUM = 25  

logging.addLevelName(ADMIN_LEVEL_NUM, 'ADMIN')

def admin(self, message, *args, **kwargs):
    if self.isEnabledFor(ADMIN_LEVEL_NUM):
        self._log(ADMIN_LEVEL_NUM, message, args, **kwargs)

logging.Logger.admin = admin
