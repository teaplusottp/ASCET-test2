# -*- coding: utf-8 -*-
class AscetDatabaseScanner:
    def __init__(self, version="6.1.4"):
        self.version = version
    def connect(self): return True
    def process_class(self, path): return True
    def disconnect(self): pass