from odoo import models, fields, api, _

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    is_return = fields.Boolean("Retorno",default=False)