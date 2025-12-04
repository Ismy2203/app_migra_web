from odoo import models, fields # type: ignore

class MigrationLog(models.Model):
    _name = 'migration.log'
    _description = 'Logs de Migración'

    migration_name = fields.Char('Nombre de la Migración', required=True)
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada'),
        ('failed', 'Fallida')
    ], default='pending', string="Estado")
    message = fields.Text('Mensaje de Error')
    migration_date = fields.Datetime('Fecha de Migración', default=fields.Datetime.now)
    model_name = fields.Char('Modelo Migrado')
