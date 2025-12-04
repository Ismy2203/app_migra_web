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
        """Iniciar la migración de los modelos configurados con manejo de relaciones."""
        _logger.info("Iniciando el proceso de migración.")

        uid = self.connect()
        if not uid:
            raise UserError("No hay conexión activa.")

        try:
            models_proxy = xmlrpc.client.ServerProxy(f"{self.source_url}/xmlrpc/2/object")
            _logger.info("Conexión establecida. Comenzando migración...")

            for model in self.model_ids:
                origin_model = model.model_origin.model
                dest_model = model.model_dest.model
                _logger.info(f"🔄 Migrando modelo {origin_model} → {dest_model}")

                fields_to_migrate = [f.field_origin_id.name for f in model.field_ids if f.field_origin_id]
                _logger.info(f"📋 Campos a migrar: {fields_to_migrate}")

                # Obtener registros desde la base origen
                records = models_proxy.execute_kw(
                    self.source_db, uid, self.source_password,
                    origin_model, 'search_read', [[]],
                    {'fields': fields_to_migrate}
                )
                _logger.info(f"📦 Registros obtenidos: {len(records)}")

                for rec in records:
                    data = {}

                    for f in model.field_ids:
                        if not f.field_origin_id or not f.field_dest_id:
                            continue

                        val = rec.get(f.field_origin_id.name)
                        dest_field_name = f.field_dest_id.name

                        # === CAMPOS RELACIONALES ===
                        if f.is_relational:
                            related_model = f.related_model or f.field_origin_id.relation
                            relation_type = f.field_origin_id.ttype
                            if not related_model:
                                _logger.warning(f"⚠ Campo {dest_field_name} es relacional pero sin modelo relacionado.")
                                continue

                            _logger.info(f"↪ Procesando campo relacional {dest_field_name} ({relation_type}) → {related_model}")

                            # Normalizamos los valores según tipo de relación
                            if not val:
                                continue

                            # --- Many2one ---
                            if relation_type == 'many2one':
                                related_id = val[0] if isinstance(val, list) else val
                                val = self._resolve_related_record(
                                    models_proxy, uid, f, related_model, related_id
                                )
                                if val:
                                    data[dest_field_name] = val

                            # --- Many2many ---
                            elif relation_type == 'many2many':
                                related_ids = []
                                for rel_id in val:
                                    resolved_id = self._resolve_related_record(
                                        models_proxy, uid, f, related_model, rel_id
                                    )
                                    if resolved_id:
                                        related_ids.append(resolved_id)
                                if related_ids:
                                    data[dest_field_name] = [(6, 0, related_ids)]

                            # --- One2many ---
                            elif relation_type == 'one2many':
                                _logger.warning(f"⚠ Campo {dest_field_name} (one2many) no se migra automáticamente.")
                                continue

                            continue  # pasar al siguiente campo

                        # === CAMPOS NORMALES ===
                        data[dest_field_name] = val

                    # Crear registro en destino
                    try:
                        self.env[dest_model].sudo().create(data)
                        _logger.info(f"✔ Registro creado en {dest_model}: {data}")
                    except Exception as e:
                        _logger.error(f"❌ Error al crear registro en {dest_model}: {str(e)}")
                        continue

            _logger.info("✅ Migración completada correctamente.")
            return True

        except Exception as e:
            _logger.error(f"Error durante la migración: {str(e)}")
            raise UserError(f"Error durante la migración: {str(e)}")


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
