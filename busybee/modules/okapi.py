from .module import Module


class Okapi(Module):

    def __init__(self, descriptor_location, jar_location, port):
        super().__init__('okapi', descriptor_location, jar_location, port)

    def build_cmd(self):
        sys_props = f'''-Dokapiurl="http://localhost:9130" \
-Dstorage=postgres \
-Dpostgres_username=folio_admin \
-Dpostgres_password=folio_admin \
-Dpostgres_database=okapi \
-Dpostgres_host=olamiebsco \
'''
        result = 'java '
        result += f'-Dhttp.port={self.http_port} \\'
        result += sys_props
        if self.debug_info is not None:
            result += f'-agentlib:jdwp=transport=dt_socket,server=y,' \
                      f'suspend={"y" if self.debug_info.suspend else "n"}' \
                      f',address=0.0.0.0:{self.debug_info.port} '
        result += f'-jar {self.jar_location} dev'
        return result
