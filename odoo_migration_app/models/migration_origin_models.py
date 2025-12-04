from odoo import models, fields # type: ignore

class MigrationOriginModels(models.Model):
    _name = 'migration.origin.models'
    _description = 'Modelos Origen'

    name = fields.Char('Nombre del modelo', required=True)
    model = fields.Char('Nombre técnico del modelo', required=True)