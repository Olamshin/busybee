from .module import Module

class Okapi(Module):

    def __init__(self, descriptor_location, jar_location, port):
        super().__init__('okapi', descriptor_location, jar_location, port)
        self.cmd = f'''java \
-Dokapiurl="http://localhost:3000" \
-Dstorage=postgres \
-Dpostgres_username=folio_admin \
-Dpostgres_password=password \
-Dpostgres_database=okapi \
-jar {self.jar_location} dev
'''