import os.path
from samuTeszt.src.common.Storage import StorageTestSuite


class LCFMapperTestClient(StorageTestSuite):
    def __init__(self):
        super().__init__(path="tests", error_path=os.path.join("..", "errors"))

