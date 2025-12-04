import logging
from odoo import models, fields, api  # type: ignore
import xmlrpc.client
from odoo.exceptions import UserError # type: ignore

_logger = logging.getLogger(__name__)


class MigrationConfig(models.Model):
    _name = 'migration.config'
    _description = 'Configuración de la migración'

    name = fields.Char('Nombre', required=True)
    source_url = fields.Char('URL Origen', required=True)
    source_db = fields.Char('Base de Datos Origen', required=True)
    source_user = fields.Char('Usuario Origen', required=True)
    source_password = fields.Char('Contraseña Origen', required=True)
    is_connected = fields.Boolean('Conectado', default=False)
    model_ids = fields.One2many('migration.model', 'config_id', string="Modelos a Migrar")
    field_ids = fields.One2many('migration.fields', 'config_id', string="Campos de Migración")
    id_mapping_ids = fields.One2many('migration.id.mapping', 'config_id', string="Mapeo de IDs")
    has_models = fields.Boolean(
        string="Tiene Modelos",
        compute="_compute_has_models",
        store=False
    )

    @api.depends('model_ids')
    def _compute_has_models(self):
        for rec in self:
            rec.has_models = bool(rec.model_ids)

    # ==========================
    # MÉTODOS DE CONEXIÓN
    # ==========================
    def connect(self):
        """Conectar al entorno de origen y verificar la conexión"""
        try:
            _logger.info(f"Intentando conectar a {self.source_url} con usuario {self.source_user}")
            common = xmlrpc.client.ServerProxy(f"{self.source_url}/xmlrpc/2/common")
            uid = common.authenticate(self.source_db, self.source_user, self.source_password, {})
            if uid:
                self.is_connected = True
                _logger.info(f"Conexión exitosa. UID: {uid}")
                return uid
            else:
                self.is_connected = False
                _logger.error("No se pudo autenticar contra la base de datos origen.")
        except Exception as e:
            self.is_connected = False
            _logger.error(f"Error al conectar: {str(e)}")
        return False

    # ==========================
    # NUEVO MÉTODO: TRAER MODELOS
    # ==========================
    def get_origin_models(self):
        """Importa los modelos desde la base de datos origen a migration.origin.models"""
        uid = self.connect()
        if not uid:
            raise UserError("No hay conexión con la base de datos origen.")

        try:
            models_proxy = xmlrpc.client.ServerProxy(f"{self.source_url}/xmlrpc/2/object")
            _logger.info("Descargando lista de modelos desde el origen...")

            records = models_proxy.execute_kw(
                self.source_db, uid, self.source_password,
                'ir.model', 'search_read', [[]], {'fields': ['model', 'name']}
            )

            created = 0
            for rec in records:
                if not self.env['migration.origin.models'].search([('model', '=', rec['model'])]):
                    self.env['migration.origin.models'].create({
                        'name': rec['name'],
                        'model': rec['model']
                    })
                    created += 1

            _logger.info(f"{created} modelos importados.")
            return True
        except Exception as e:
            _logger.error(f"Error al traer modelos: {str(e)}")
            raise UserError(f"Error al traer modelos: {str(e)}")

    # ==========================
    # MIGRACIÓN PRINCIPAL
    # ==========================
    def start_migration(self):
        """Iniciar la migración con mapeo persistente de IDs."""
        _logger.info("🚀 Iniciando migración con mapeo de IDs...")

        uid = self.connect()
        if not uid:
            raise UserError("No hay conexión activa.")

        # Limpiar mapeos anteriores
        self.id_mapping_ids.unlink()

        try:
            models_proxy = xmlrpc.client.ServerProxy(f"{self.source_url}/xmlrpc/2/object")
            
            for model in self.model_ids:
                origin_model = model.model_origin.model
                dest_model = model.model_dest.model
                _logger.info(f"🔄 Migrando modelo {origin_model} → {dest_model}")

                # Obtener solo campos mapeados
                fields_to_fetch = [f.field_origin_id.name for f in model.field_ids if f.field_origin_id]
                fields_to_fetch.append('id')  # Siempre traer el ID
                
                _logger.info(f"📋 Campos a traer: {fields_to_fetch}")

                # Traer registros del origen
                records = models_proxy.execute_kw(
                    self.source_db, uid, self.source_password,
                    origin_model, 'search_read', [[]],
                    {'fields': fields_to_fetch}
                )
                _logger.info(f"📦 {len(records)} registros obtenidos")

                # Procesar cada registro
                for rec in records:
                    source_record_id = rec['id']
                    data = {}

                    for field_map in model.field_ids:
                        if not field_map.field_origin_id or not field_map.field_dest_id:
                            continue

                        origin_field_name = field_map.field_origin_id.name
                        dest_field_name = field_map.field_dest_id.name
                        val = rec.get(origin_field_name)

                        # === CAMPOS RELACIONALES ===
                        if field_map.is_relational:
                            val = self._resolve_relation_with_mapping(
                                models_proxy, uid, field_map, val, source_record_id
                            )
                            if val is None and field_map.not_found_action == 'skip':
                                _logger.warning(f"⏭️  Saltando registro {source_record_id} por relación no encontrada")
                                break
                        
                        if val is not None:
                            data[dest_field_name] = val

                    # Crear registro en destino si no se saltó
                    if data:
                        try:
                            new_rec = self.env[dest_model].sudo().create(data)
                            
                            # 🔥 GUARDAR MAPEO ID
                            self.env['migration.id.mapping'].create({
                                'config_id': self.id,
                                'model_name': dest_model,
                                'source_id': source_record_id,
                                'dest_id': new_rec.id,
                            })
                            
                            _logger.info(f"✅ Creado {dest_model} ID {new_rec.id} (origen: {source_record_id})")
                            
                        except Exception as e:
                            _logger.error(f"❌ Error creando registro {source_record_id}: {str(e)}")
                            # Crear log de error
                            self.env['migration.log'].create({
                                'migration_name': self.name,
                                'status': 'failed',
                                'message': f"Error en {dest_model} ID {source_record_id}: {str(e)}",
                                'model_name': dest_model,
                            })

            _logger.info("✅ Migración completada")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Migración Completada',
                    'message': f'{len(self.id_mapping_ids)} registros migrados',
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            _logger.error(f"💥 Error durante migración: {str(e)}")
            raise UserError(f"Error durante la migración: {str(e)}")

    def _resolve_relation_with_mapping(self, models_proxy, uid, field_config, origin_value, source_record_id):
        """Resuelve relaciones usando mapeo de IDs persistente."""
        
        if not origin_value:
            return None

        related_model = field_config.related_model or field_config.field_origin_id.relation
        relation_type = field_config.field_origin_id.ttype

        _logger.info(f"🔗 Resolviendo {field_config.field_dest_id.name} ({relation_type}) → {related_model}")

        # === MANY2ONE ===
        if relation_type == 'many2one':
            origin_id = origin_value[0] if isinstance(origin_value, list) else origin_value
            
            # 1. Buscar en mapeo primero
            mapping = self.env['migration.id.mapping'].search([
                ('config_id', '=', self.id),
                ('model_name', '=', related_model),
                ('source_id', '=', origin_id),
            ], limit=1)
            
            if mapping:
                _logger.info(f"✓ Encontrado en mapeo: {origin_id} → {mapping.dest_id}")
                return mapping.dest_id
            
            # 2. Si no está en mapeo, buscar/crear
            dest_id = self._search_or_create_related(models_proxy, uid, field_config, related_model, origin_id)
            
            if dest_id:
                # Guardar en mapeo para futuras referencias
                self.env['migration.id.mapping'].create({
                    'config_id': self.id,
                    'model_name': related_model,
                    'source_id': origin_id,
                    'dest_id': dest_id,
                })
                return dest_id
            
            return None

        # === MANY2MANY ===
        elif relation_type == 'many2many':
            dest_ids = []
            for origin_id in origin_value:
                dest_id = self._resolve_relation_with_mapping(
                    models_proxy, uid, field_config, origin_id, source_record_id
                )
                if dest_id:
                    dest_ids.append(dest_id)
            
            return [(6, 0, dest_ids)] if dest_ids else None

        # === ONE2MANY ===
        elif relation_type == 'one2many':
            _logger.warning(f"⚠️  One2many no soportado aún: {field_config.field_dest_id.name}")
            return None

        return None


    def _search_or_create_related(self, models_proxy, uid, field_config, related_model, remote_id):
        """Busca o crea registro relacionado (lógica existente mejorada)."""
        
        try:
            # Campos para buscar
            search_fields = [f.name for f in field_config.fields_to_search] if field_config.fields_to_search else ['name']
            search_fields.append('id')
            
            _logger.info(f"🔍 Buscando {related_model} ID {remote_id} por campos: {search_fields}")

            # Traer datos del registro remoto
            remote_data = models_proxy.execute_kw(
                self.source_db, uid, self.source_password,
                related_model, 'read', [remote_id],
                {'fields': search_fields}
            )

            if not remote_data:
                _logger.warning(f"⚠️  Registro remoto {remote_id} no existe en {related_model}")
                return None

            remote_data = remote_data[0]
            _logger.info(f"📄 Datos remotos: {remote_data}")

            # Construir dominio de búsqueda
            domain = []
            for field in field_config.fields_to_search:
                field_value = remote_data.get(field.name)
                if field_value:
                    # Si es relacional, tomar solo el ID
                    if isinstance(field_value, (list, tuple)):
                        field_value = field_value[0]
                    domain.append((field.name, '=', field_value))

            if not domain:
                _logger.warning(f"⚠️  No se pudo construir dominio de búsqueda")
                return None

            _logger.info(f"🧭 Buscando en destino con dominio: {domain}")

            # Buscar en destino
            matches = self.env[related_model].sudo().search(domain)
            _logger.info(f"🔢 Coincidencias: {len(matches)}")

            # Sin coincidencias
            if not matches:
                if field_config.not_found_action == 'create':
                    vals = {f.name: remote_data[f.name] 
                        for f in field_config.fields_to_search 
                        if remote_data.get(f.name)}
                    new_rec = self.env[related_model].sudo().create(vals)
                    _logger.info(f"🆕 Creado {related_model} ID {new_rec.id}")
                    return new_rec.id
                return None

            # Múltiples coincidencias
            if len(matches) > 1:
                if field_config.duplicate_action == 'first':
                    _logger.warning(f"⚠️  {len(matches)} duplicados, tomando primero")
                    return matches[0].id
                elif field_config.duplicate_action == 'skip':
                    return None
                else:
                    raise UserError(f"Duplicados en {related_model}: {domain}")

            return matches.id

        except Exception as e:
            _logger.error(f"❌ Error resolviendo relación: {str(e)}")
            return None


    def _resolve_related_record(self, models_proxy, uid, field_config, related_model, remote_id):
        """Busca o crea un registro relacionado según configuración."""
        try:
            related_fields = [fld.name for fld in field_config.fields_to_search]
            _logger.info(f"🔍 Resolviendo relación {field_config.field_dest_id.name} "
                        f"→ {related_model} (remote_id={remote_id}, fields={related_fields})")

            related_record = models_proxy.execute_kw(
                self.source_db, uid, self.source_password,
                related_model, 'read', [remote_id],
                {'fields': related_fields}
            )

            if not related_record:
                _logger.warning(f"⚠ Registro relacionado ID {remote_id} no encontrado en {related_model}")
                return None

            record_data = related_record[0]
            _logger.info(f"📄 Datos del registro remoto: {record_data}")

            # Construir dominio para búsqueda
            domain = [(fld.name, '=', record_data[fld.name])
                    for fld in field_config.fields_to_search
                    if record_data.get(fld.name)]

            _logger.info(f"🧭 Dominio de búsqueda para {related_model}: {domain}")

            matches = self.env[related_model].sudo().search(domain)
            _logger.info(f"🔢 Coincidencias encontradas: {len(matches)}")

            # --- Crear si no existe ---
            if not matches:
                if field_config.not_found_action == 'create':
                    vals_to_create = {
                        fld.name: record_data[fld.name]
                        for fld in field_config.fields_to_search
                        if record_data.get(fld.name)
                    }
                    new_rec = self.env[related_model].sudo().create(vals_to_create)
                    _logger.info(f"🆕 Creado nuevo registro en {related_model}: {vals_to_create}")
                    return new_rec.id
                _logger.info(f"⏭ Registro no encontrado en {related_model}, saltando...")
                return None

            # --- Duplicados ---
            if len(matches) > 1:
                if field_config.duplicate_action == 'first':
                    _logger.warning(f"⚠ Duplicados en {related_model}, tomando el primero.")
                    return matches[0].id
                elif field_config.duplicate_action == 'skip':
                    _logger.warning(f"⚠ Duplicados encontrados en {related_model}, registro saltado.")
                    return None
                else:
                    raise UserError(f"Duplicados detectados en {related_model} para dominio {domain}.")

            return matches.id

        except Exception as e:
            _logger.error(f"❌ Error resolviendo relación en {related_model}: {str(e)}")
            return None
