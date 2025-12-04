import logging
from odoo import models, fields, api  # type: ignore
import xmlrpc.client
from odoo.exceptions import UserError # type: ignore

_logger = logging.getLogger(__name__)

class MigrationModel(models.Model):
    _name = 'migration.model'
    _description = 'Modelos a Migrar'

    model_origin = fields.Many2one('migration.origin.models', string="Modelo Origen")
    model_dest = fields.Many2one('ir.model', string="Modelo Destino")
    field_ids = fields.One2many('migration.fields', 'model_id', string="Campos de Migración")
    config_id = fields.Many2one('migration.config', string="Configuración de Migración")
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('config_id') and self.env.context.get('active_id'):
                vals['config_id'] = self.env.context['active_id']
        return super().create(vals_list)

    
    def action_get_fields(self):
        """Trae los campos técnicos del modelo origen remoto."""
        self.ensure_one()
        config = self.config_id
        uid = config.connect()
        if not uid:
            raise UserError("No hay conexión con la base de datos origen.")

        model_origin = self.model_origin
        if not model_origin:
            raise UserError("Selecciona un modelo origen antes de traer los campos.")

        _logger.info(f"📥 Obteniendo campos técnicos del modelo remoto: {model_origin.model}")

        models_proxy = xmlrpc.client.ServerProxy(f"{config.source_url}/xmlrpc/2/object")

        # Aquí nos aseguramos de traer solo los campos técnicos
        fields_data = models_proxy.execute_kw(
            config.source_db, uid, config.source_password,
            'ir.model.fields', 'search_read',
            [[('model', '=', model_origin.model)]],
            {'fields': ['name', 'ttype', 'relation']} 
        )

        if not fields_data:
            _logger.warning(f"No se encontraron campos en el modelo remoto {model_origin.model}")
            return

        count = 0
        for f in fields_data:
            field_name = f.get('name')
            field_type = f.get('ttype')
            relation = f.get('relation')

            if not field_name:
                continue

            exists = self.env['migration.origin.fields'].search([
                ('name', '=', field_name),
                ('model_id', '=', model_origin.id)
            ], limit=1)

            if not exists:
                self.env['migration.origin.fields'].create({
                    'name': field_name,
                    'model_id': model_origin.id,
                    'ttype': field_type,
                    'relation': relation
                })
                count += 1

        _logger.info(f"✅ {count} campos técnicos importados para {model_origin.model}.")
