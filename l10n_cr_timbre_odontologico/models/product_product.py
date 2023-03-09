
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = "product.product"

    exent_product = fields.Boolean("Excento Pr.",related="product_tmpl_id.exent_product")
    percentage_value = fields.Float("Porcentaje Ex.",related="product_tmpl_id.percentage_value")

class ProductElectronic(models.Model):
    _inherit = "product.template"

    exent_product = fields.Boolean("Excento")
    percentage_value = fields.Float("Porcentaje")