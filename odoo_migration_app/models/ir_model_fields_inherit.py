from odoo import models, fields, api

class IrModelFieldsInherit(models.Model):
    _inherit = 'ir.model.fields'

    # Mostramos "nombre técnico (descripción)"
    display_name = fields.Char(
        compute='_compute_display_name',
        store=False
    )

    @api.depends('name', 'field_description')
    def _compute_display_name(self):
        """Combina el nombre técnico con la descripción legible."""
        for rec in self:
            if rec.field_description:
                rec.display_name = f"{rec.name} ({rec.field_description})"
            else:
                rec.display_name = rec.name

    def name_get(self):
        """Muestra el nombre técnico con la descripción."""
        result = []
        for rec in self:
            name = rec.display_name or rec.name
            result.append((rec.id, name))
        return result

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Permite buscar por nombre técnico o descripción."""
        args = args or []
        domain = ['|', ('name', operator, name), ('field_description', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return recs.name_get()
