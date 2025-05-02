from xmlrpc import client

class OdooConnection:
    def __init__(self, url, db, user, password):
        self.url = url.rstrip("/")
        self.db = db
        self.user = user
        self.password = password
        self.uid = None
        self.models = None

    def authenticate(self):
        common = client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(self.db, self.user, self.password, {})
        if not self.uid:
            raise Exception("Autenticación fallida. Verifica tus credenciales.")
        self.models = client.ServerProxy(f"{self.url}/xmlrpc/2/object")
        return True

    def get_model_list(self, limit=1000):
        if not self.models:
            raise Exception("No hay conexión establecida.")
        model_list = self.models.execute_kw(
            self.db, self.uid, self.password,
            'ir.model', 'search_read', [[]],
            {'fields': ['model'], 'limit': limit}
        )
        return sorted([m['model'] for m in model_list])

    def get_fields(self, model, attributes=['string']):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'fields_get', [],
            {'attributes': attributes}
        )

    def search(self, model, domain):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'search', [domain]
        )

    def read(self, model, ids, fields):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'read', [ids],
            {'fields': fields}
        )

    def create(self, model, values):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'create', [values]
        )

    def write(self, model, ids, values):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'write', [ids, values]
        )

    def search_read(self, model, domain, fields):
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, 'search_read', [domain],
            {'fields': fields}
        )
