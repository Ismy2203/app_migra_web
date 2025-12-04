from odoo import models, fields # type: ignore

class MigrationTest(models.Model):
    _name = 'migration.test'
    _description = 'Prueba de Migración'

    name = fields.Char('Nombre de la Prueba', required=True)
    status = fields.Selection([
        ('pending', 'Pendiente'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada'),
        ('failed', 'Fallida')
    ], default='pending', string="Estado")
    message = fields.Text('Mensaje de Error')
    test_date = fields.Datetime('Fecha de la Prueba', default=fields.Datetime.now)
