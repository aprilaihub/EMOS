from Information_Units.Databases.BaseDatabase import BaseDatabase


class JarvisdftDatabase(BaseDatabase):
    def __init__(self, database_name, logger=None):
        super().__init__(database_name, logger)
    
    def info(self):
        msg = "JARVIS-DFT - NIST computational materials database with electronic, optical, and solar cell properties"
        return msg

    def retrieve(self, inputs: dict) -> str:
        # Implement retrieve logic here
        if self.logger:
            self.logger.log("Retrieved from JarvisDFT")
        return None
