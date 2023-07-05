from abc import ABC, abstractmethod

class Logger(ABC):
    @abstractmethod
    def log(self, message):
        pass

class FileLogger(Logger):
    def logx(self, message):
        # Log the message to a file
        pass

class UserService:
    def __init__(self, logger: Logger):
        self.logger = logger

    def register(self, username):
        self.logger.log(f"User '{username}' registered.")

# Usage
logger = FileLogger()  # Concrete implementation
user_service = UserService(logger)
user_service.register("John")
