
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    exent_product = fields.Boolean("Afecta Timbre Odontologico",related="product_tmpl_id.exent_product")
    economic_activity_id = fields.Many2one("economic.activity","Actividad económica por defecto",related="product_tmpl_id.economic_activity_id")
    service_medic = fields.Boolean("Es Servicio Medico", related='product_tmpl_id.service_medic')
class ProductElectronic(models.Model):
    _inherit = "product.template"

    exent_product = fields.Boolean("Afecta Timbre Odontologico")
    economic_activity_id = fields.Many2one("economic.activity","Actividad económica por defecto",domain="[('active','=',True)]")
    service_medic = fields.Boolean("Es Servicio Medico")