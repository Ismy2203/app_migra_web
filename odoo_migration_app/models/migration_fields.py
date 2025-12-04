from odoo import models, fields, api # type: ignore
import logging

_logger = logging.getLogger(__name__)


class MigrationField(models.Model):
    _name = 'migration.fields'
    _description = 'Campos de Migración'

    # === Relaciones base ===
    model_id = fields.Many2one('migration.model', string="Modelo de Migración", required=True)
    config_id = fields.Many2one(
        'migration.config',
        string="Configuración de Migración",
        related='model_id.config_id',
        store=True
    )

    # === Campos principales ===
    field_origin_id = fields.Many2one(
        'migration.origin.fields',
        string="Campo Origen",
        help="Campo del modelo en la base de datos origen (remota)."
    )

    field_dest_id = fields.Many2one(
        'ir.model.fields',
        string="Campo Destino",
        help="Campo equivalente en la base de datos actual (destino)."
    )

    # === Información del campo ===
    is_relational = fields.Boolean(
        string='Es Relacional?',
        compute='_compute_field_metadata',
        store=True
    )
    related_model = fields.Char(
        string='Modelo Relacionado',
        compute='_compute_field_metadata',
        store=True
    )
    field_type = fields.Char(
        string='Tipo de Campo',
        compute='_compute_field_metadata',
        store=True
    )

    # === Configuración avanzada para campos relacionales ===
    fields_to_search = fields.Many2many(
        'ir.model.fields',
        string="Campos de Búsqueda",
        help="Campos del modelo relacionado (destino) que se usarán para buscar coincidencias.",
        widget='many2many_tags'
    )

    not_found_action = fields.Selection([
        ('skip', 'Saltar registro'),
        ('create', 'Crear nuevo registro'),
    ], string="Si no existe en destino", default='skip')

    duplicate_action = fields.Selection([
        ('first', 'Tomar el primero'),
        ('skip', 'Saltar registro'),
        ('error', 'Generar error'),
    ], string="Si hay duplicados", default='first')
    
    # === Cómputos automáticos ===
    @api.depends('field_origin_id')
    def _compute_field_metadata(self):
        """Rellena automáticamente tipo, modelo relacionado y si es relacional."""
        for rec in self:
            if not rec.field_origin_id:
                rec.field_type = False
                rec.related_model = False
                rec.is_relational = False
                continue

            rec.field_type = rec.field_origin_id.ttype
            rec.related_model = rec.field_origin_id.relation or ''
            rec.is_relational = bool(rec.related_model)

            _logger.debug(
                f"[FIELD META] {rec.field_origin_id.name} → "
                f"type={rec.field_type}, relation={rec.related_model}, relational={rec.is_relational}"
            )

    @api.onchange('model_id', 'related_model', 'field_origin_id')
    def _onchange_domains(self):
        """Actualiza los dominios dinámicos según el modelo de migración y el modelo relacionado."""
        for rec in self:
            domain_origin = []
            domain_dest = []
            domain_search = []

            # --- Campos del modelo origen (remoto)
            if rec.model_id.model_origin:
                domain_origin = [('model_id.model', '=', rec.model_id.model_origin.model)]

            # --- Campos del modelo destino (actual)
            if rec.model_id.model_dest:
                domain_dest = [('model', '=', rec.model_id.model_dest.model)]

            # --- Campos del modelo relacionado (para búsqueda)
            if rec.related_model:
                domain_search = [('model', '=', rec.related_model)]

            _logger.info(
                f"[onchange_domains] → origen={domain_origin}, destino={domain_dest}, búsqueda={domain_search}"
            )

            return {
                'domain': {
                    'field_origin_id': domain_origin,
                    'field_dest_id': domain_dest,
                    'fields_to_search': domain_search,
                }
            }
