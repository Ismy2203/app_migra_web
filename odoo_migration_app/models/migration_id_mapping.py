from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class MigrationIdMapping(models.Model):
    _name = 'migration.id.mapping'
    _description = 'Mapeo de IDs Origen → Destino'
    _rec_name = 'display_name'

    config_id = fields.Many2one('migration.config', string="Configuración", required=True, ondelete='cascade')
    model_name = fields.Char('Modelo', required=True, index=True)
    source_id = fields.Integer('ID Origen', required=True, index=True)
    dest_id = fields.Integer('ID Destino', required=True, index=True)
    xmlid = fields.Char('XML ID', help="External ID si existe")
    display_name = fields.Char('Nombre', compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('unique_mapping', 'unique(config_id, model_name, source_id)', 
         'Ya existe un mapeo para este registro origen!')
    ]

    @api.depends('model_name', 'source_id', 'dest_id')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.model_name}: {rec.source_id} → {rec.dest_id}"