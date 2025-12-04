from odoo import models, fields # type: ignore

class MigrationOriginFields(models.Model):
    _name = 'migration.origin.fields'
    _description = 'Campos Origen'

    name = fields.Char('Nombre técnico del campo', required=True)
    model_id = fields.Many2one('migration.origin.models', string="Modelo", required=True)
    ttype = fields.Char('Tipo de campo', required=True)
    relation = fields.Char('Modelo relacionado')
